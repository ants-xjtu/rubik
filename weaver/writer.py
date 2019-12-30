from __future__ import annotations
from weaver.auxiliary import reg_aux
from weaver.code import AggValue, If, SetValue, Command
from weaver.stock.reg import instance_table, sequence, runtime, header_parser
from weaver.util import make_block
from weaver.header import LocateStruct
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from weaver.writer_context import ValueContext, InstrContext
    from weaver.header import ParseAction
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
        values_text = ('(' + context.write_value(value) + ')' for value in context.value.values)
        return self.cexpr_template.format(*values_text)


class InstrWriter:
    # fallback
    def write(self, context: InstrContext) -> str:
        if isinstance(context.instr, If):
            text = f'if ({context.write_value(context.instr.cond)}) '
            text += make_block('\n'.join(context.write_instr(instr) for instr in context.instr.yes))
            text += ' else '
            text += make_block('\n'.join(context.write_instr(instr) for instr in context.instr.no))
            return text
        elif isinstance(context.instr, SetValue):
            assert not isinstance(context.instr, Command)
            # if isinstance(context.instr, Command):
            #     return '<placeholder>'
            # # only registers that has been set value will be declared
            # # this may help find bugs related to use-before-assignment bugs
            # context.recurse_context.global_context.decl_regs.add(context.instr.reg)
            text = f'{reg_aux.write(context, context.instr.reg)} = ({reg_aux[context.instr.reg].type_decl()})({context.write_value(context.instr.value)});'
            return text
        else:
            assert False, 'should call `write` on subclasses'
            # return '<placeholder>'


class InstExistWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        assert context.instr_context.recurse_context.inst_struct is not None
        return context.instr_context.recurse_context.inst_struct.name()


class PrefetchInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        assert context.recurse_context.key_struct is not None
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        assert len(context.instr.args) == len(context.recurse_context.key_struct.regs)
        text_lines = []
        for reg, arg in zip(context.recurse_context.key_struct.regs, context.instr.args):
            text_lines.append(context.write_instr(SetValue(reg, arg)))
        text_lines.append(
            f'{context.recurse_context.inst_struct.name()} = WV_FetchInst(&runtime->tables[{context.recurse_context.layer_id}], {context.recurse_context.instance_key()});'
        )
        return '\n'.join(text_lines)


class CreateInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        inst_name = context.recurse_context.inst_struct.name()
        return f'{inst_name} = WV_CreateInst(&runtime->tables[{context.recurse_context.layer_id}], {context.recurse_context.instance_key()}, sizeof(*{inst_name}));'


class FetchInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        return '// fetch placeholder'


class SetInstValueWriter(InstrWriter):
    def __init__(self, key: Reg):
        super(SetInstValueWriter, self).__init__()
        self.key = key

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        assert len(context.instr.args) == 1
        return f'{reg_aux.write(context, self.key)} = {context.write_value(context.instr.args[0])};'


class InsertMetaWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        assert len(context.instr.args) == 3
        assert instance_table in context.instr.args[0].regs
        assert context.recurse_context.inst_struct is not None
        offset, length = context.instr.args[1], context.instr.args[2]
        return f'WV_InsertMeta(&{context.recurse_context.inst_struct.name()}->seq, {context.write_value(offset)}, {context.write_value(length)});'


class InsertDataWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        assert len(context.instr.args) == 2
        assert instance_table in context.instr.args[0].regs
        assert context.recurse_context.inst_struct is not None
        data = context.instr.args[1]
        return f'WV_InsertData(&{context.recurse_context.inst_struct.name()}->seq, {context.write_value(data)});'


class SeqReadyWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        assert sequence in context.value.regs
        assert context.instr_context.recurse_context.inst_struct is not None
        return f'WV_SeqReady(&{context.instr_context.recurse_context.inst_struct.name()}->seq)'


class SeqAssembleWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        assert context.recurse_context.inst_struct is not None
        return f'{context.recurse_context.content_name()} = WV_SeqAssemble(&{context.recurse_context.inst_struct.name()}->seq);'


class DestroyInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        return f'WV_DestroyInst(&runtime->tables[{context.recurse_context.layer_id}], {context.recurse_context.instance_key()});'


class NextWriter(InstrWriter):
    def __init__(self, content: bool = False):
        super(NextWriter, self).__init__()
        self.content = content

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == runtime
        next_entry = context.recurse_context.global_context.next_table[context.instr].block_id
        return (
            ('', f'current = {context.recurse_context.content_name()};\n')[self.content] +
            f'goto L{next_entry}; L{next_entry}_Ret:'
        )


class ParseHeaderWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == header_parser
        return self.write_actions(context.recurse_context.actions)

    def write_actions(self, actions: List[ParseAction]) -> str:
        text = ''
        for action in actions:
            for struct in action.iterate_structs():
                text += f'{struct.name()} = NULL;\n'
            if isinstance(action, LocateStruct):
                text += f'{action.struct.name()} = (void *)current.cursor;\n'
                text += f'current = WV_SliceAfter(current, {action.struct.byte_length});'
            else:
                # TODO
                raise NotImplementedError()
        return text


class CallWriter(InstrWriter):
    def __init__(self, name: str, regs: List[Reg]):
        super(CallWriter, self).__init__()
        self.name = name
        self.regs = regs

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == runtime
        decl_core = f'WV_U8 {self.name}({", ".join(reg_aux[reg].type_decl() + f" _{i}" for i, reg in enumerate(self.regs))})'
        context.recurse_context.global_context.insert_call_decl(self.name, decl_core + ' ' + make_block("//"))
        return (
            f'{decl_core};\n'
            f'{self.name}({", ".join(reg_aux.write(context, reg) for reg in self.regs)});'
        )


class PayloadWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return 'current'
