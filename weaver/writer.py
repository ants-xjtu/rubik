from __future__ import annotations
from weaver.auxiliary import reg_aux
from weaver.code import AggValue, If, SetValue, Command
from weaver.stock.reg import instance_table, sequence, runtime, header_parser
from weaver.util import make_block
from weaver.header import *
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from weaver.writer_context import ValueContext, InstrContext
    from weaver.code import Reg


class ValueWriter:
    # fallback
    def write(self, context: ValueContext) -> str:
        if isinstance(context.value, AggValue):
            return AggValueWriter(context.value.agg_eval).write(context)
        else:
            return TemplateValueWriter(context.value.eval_template).write(context)


class TemplateValueWriter(ValueWriter):
    def __init__(self, cexpr_template: str):
        self.cexpr_template = cexpr_template

    def write(self, context: ValueContext) -> str:
        return self.cexpr_template.format(
            *(reg_aux.write(context.instr_context, reg) for reg in context.value.regs))


class AggValueWriter(ValueWriter):
    def __init__(self, cexpr_template: str):
        super().__init__()
        self.cexpr_template = cexpr_template

    def write(self, context: ValueContext) -> str:
        assert isinstance(context.value, AggValue)
        values_text = ('(' + context.write_value(value) +
                       ')' for value in context.value.values)
        return self.cexpr_template.format(*values_text)


class InstrWriter:
    # fallback
    def write(self, context: InstrContext) -> str:
        if isinstance(context.instr, If):
            text = f'if ({context.write_value(context.instr.cond)}) '
            text += make_block('\n'.join(context.write_instr(instr)
                                         for instr in context.instr.yes))
            text += ' else '
            text += make_block('\n'.join(context.write_instr(instr)
                                         for instr in context.instr.no))
            return text
        elif isinstance(context.instr, SetValue):
            assert not isinstance(context.instr, Command)
            text = f'{reg_aux.write(context, context.instr.reg)} = ({reg_aux[context.instr.reg].type_decl()})({context.write_value(context.instr.value)});'
            return text
        else:
            assert False, 'should call `write` on subclasses'


class InstExistWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        assert context.instr_context.recurse_context.inst_struct is not None
        return context.instr_context.recurse_context.prefetch_name()


class PrefetchInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        text = ''
        lid = context.recurse_context.layer_id
        pre_k = f'runtime->{context.recurse_context.prealloc()}->k'
        for reg in context.recurse_context.inst_struct.create_aux().key_regs:
            text += f'{pre_k}._{reg} = {reg_aux.write(context, reg)};\n'
        text += f'{context.recurse_context.prefetch_name()} = tommy_hashdyn_search(&runtime->hash_{lid}, {context.recurse_context.eq_func_name()}, &{pre_k}, hash(&{pre_k}, sizeof({context.recurse_context.key_struct_name()})));'
        return text


class CreateInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        lid = context.recurse_context.layer_id
        pre = f'runtime->prealloc_{lid}'
        inst_aux = context.recurse_context.inst_struct.create_aux()
        # TODO: BiInst
        return (
            f'tommy_hashdyn_insert(\n' + 
            f'  &runtime->hash_{lid}, &{pre}->node, {pre}, hash(&{pre}->k,\n' + 
            f'  sizeof({context.recurse_context.key_struct_name()}))\n' + 
            f');\n'
            f'{context.recurse_context.prefetch_name()} = (WV_Any)({inst_aux.name()} = {pre});\n'
            f'WV_InitSeq(&{inst_aux.name()}->seq);\n'
            f'{pre} = malloc({inst_aux.sizeof()});\n'
            f'memset({pre}, 0, sizeof({inst_aux.typedef()}));'
        )


class FetchInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        inst_name = context.recurse_context.inst_struct.create_aux().name()
        # TODO: BiInst
        return f'{inst_name} = (WV_Any){context.recurse_context.prefetch_name()};'


class InsertMetaWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        # TODO: BiInst
        # assert len(context.instr.args) == 3
        assert instance_table in context.instr.args[0].regs
        assert context.recurse_context.inst_struct is not None
        offset, data = context.instr.args[1], context.instr.args[2]
        return f'WV_InsertMeta(&{context.recurse_context.prefetch_name()}->seq, {context.write_value(offset)}, {context.write_value(data)});'


class InsertDataWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        # TODO: BiInst
        # assert len(context.instr.args) == 3
        assert instance_table in context.instr.args[0].regs
        assert context.recurse_context.inst_struct is not None
        offset, data = context.instr.args[1], context.instr.args[2]
        return f'WV_InsertData(&{context.recurse_context.prefetch_name()}->seq, {context.write_value(offset)}, {context.write_value(data)});'


class SeqReadyWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        assert sequence in context.value.regs
        assert context.instr_context.recurse_context.inst_struct is not None
        return f'WV_SeqReady(&{context.instr_context.recurse_context.prefetch_name()}->seq)'


class SeqAssembleWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        assert context.recurse_context.inst_struct is not None
        return f'{context.recurse_context.content_name()} = WV_SeqAssemble(&{context.recurse_context.inst_struct.create_aux().name()}->seq, &nf{context.recurse_context.layer_id});'


class DestroyInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        lid = context.recurse_context.layer_id
        prefetch = context.recurse_context.prefetch_name()
        return (
            f'tommy_hashdyn_remove(&runtime->hash_{lid}, {context.recurse_context.eq_func_name()}, {prefetch}, hash(&{prefetch}->k, sizeof({context.recurse_context.key_struct_name()})));\n'
            f'WV_CleanSeq(&{prefetch}->seq);\n'
            f'free({prefetch});'
        )

class NextWriter(InstrWriter):
    def __init__(self, content: bool = False):
        super(NextWriter, self).__init__()
        self.content = content

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == runtime
        next_entry = context.recurse_context.global_context.next_table[context.instr].block_id
        self_index = context.recurse_context.global_context.next_index[context.instr]
        return (
            ('', f'current = {context.recurse_context.content_name()};\n')[self.content] +
            'WV_U8 old_target = ret_target;\n' +
            f'ret_target = {self_index}; goto L{next_entry}; NI{self_index}_Ret:\n' +
            'ret_target = old_target;'
        )


class ParseHeaderWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == header_parser
        return 'saved = current;\n' + self.write_actions(context.recurse_context.actions, context)

    def write_actions(self, actions: List[ParseAction], context: InstrContext) -> str:
        lines = []
        for action in actions:
            for struct in action.iterate_structs():
                lines.append(f'{struct.create_aux().name()} = NULL;')
            if isinstance(action, LocateStruct):
                lines.append(f'{action.struct.create_aux().name()} = (WV_Any)current.cursor;')
                lines.append(f'current = WV_SliceAfter(current, {action.struct.byte_length});')
            elif isinstance(action, ParseByteSlice):
                assert reg_aux[action.slice_reg].byte_len is None
                reg_text = reg_aux.write(context, action.slice_reg)
                lines.append(f'{reg_text}.cursor = current.cursor;')
                lines.append(f'{reg_text}.length = {context.write_value(action.byte_length)};')
                lines.append(f'current = WV_SliceAfter(current, {reg_text}.length);')
            elif isinstance(action, TaggedParseLoop):
                assert reg_aux[action.tag].byte_len == 1  # no ntoh issue
                tag_text = reg_aux.write(context, action.tag)
                lines.append(f'while ({context.write_value(action.cond)}) ' + make_block('\n'.join([
                    f'{tag_text} = (({reg_aux[action.tag].type_decl()} *)current.cursor)[0];',
                    f'current = WV_SliceAfter(current, {reg_aux[action.tag].byte_len});',
                    f'switch ({tag_text}) ' + make_block('\n'.join(
                        (f'case {match}: ' if match is not None else 'default: ') + 
                        make_block(self.write_actions(actions, context) + '\ncontinue;')
                        for match, actions in action.action_map.items()
                    )),
                ])))
            else:
                assert False
        return '\n'.join(lines)


class CallWriter(InstrWriter):
    def __init__(self, name: str, regs: List[Reg] = None):
        super(CallWriter, self).__init__()
        self.name = name
        self.regs = regs or []

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == runtime
        context.recurse_context.global_context.required_calls[self.name] = self.regs
        return f'{self.name}({", ".join(reg_aux.write(context, reg) for reg in self.regs)});'


class PayloadWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return 'current'


class PayloadLengthWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return 'current->length'


class ParsedLengthWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return 'current.cursor - saved.cursor'


class TotalLengthWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return 'saved.length'
