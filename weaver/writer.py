from __future__ import annotations

from weaver.auxiliary import reg_aux
from weaver.code import AggValue, If, SetValue, Command
from weaver.code.reg import instance_table, sequence
from weaver.util import make_block
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weaver.writer_context import ValueContext, InstrContext


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
        return self.cexpr_template.format(*(f'_{reg}' for reg in context.value.regs))


class AggValueWriter(ValueWriter):
    def __init__(self, cexpr_template: str):
        super().__init__()
        self.cexpr_template = cexpr_template

    def write(self, context: ValueContext) -> str:
        assert isinstance(context.value, AggValue)
        values_text = ('(' + context.write_value(value) + ')' for value in context.value.values)
        return self.cexpr_template.format(*values_text)


class InstValueWriter(ValueWriter):
    def __init__(self, key):
        self.key = key

    def write(self, context: ValueContext) -> str:
        assert instance_table in context.value.regs
        return f'layer{context.instr_context.recurse_context.layer_id}_inst->{self.key}'


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
            # assert not isinstance(context.instr, Command)
            if isinstance(context.instr, Command):
                return '<placeholder>'
            # only registers that has been set value will be declared
            # this may help find bugs related to use-before-assignment bugs
            context.recurse_context.global_context.decl_regs.add(context.instr.reg)
            text = f'_{context.instr.reg} = ({reg_aux[context.instr.reg].type_decl()})({context.write_value(context.instr.value)});'
            return text
        else:
            # assert False, 'should call `write` on subclasses'
            return '<placeholder>'


class InstExistWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return f'WV_InstExist(&runtime->tables[{context.instr_context.recurse_context.layer_id}], ...)'


class GetInstWriter(InstrWriter):
    def __init__(self, method: str):
        super().__init__()
        assert method in {'Create', 'Fetch'}
        self.method = method

    def write(self, context: InstrContext) -> str:
        layer_id = context.recurse_context.layer_id
        return f'layer{layer_id}_inst = WV_{self.method}Inst(&runtime->tables[{layer_id}], ...);'


class SetInstValueWriter(InstrWriter):
    def __init__(self, key):
        super(SetInstValueWriter, self).__init__()
        self.key = key

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        assert len(context.instr.args) == 1
        return f'layer{context.recurse_context.layer_id}_inst->{self.key} = {context.write_value(context.instr.args[0])};'


class InsertMetaWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        assert len(context.instr.args) == 3
        assert instance_table in context.instr.args[0].regs
        offset, length = context.instr.args[1], context.instr.args[2]
        return f'WV_InsertMeta(&layer{context.recurse_context.layer_id}_inst->seq, {context.write_value(offset)}, {context.write_value(length)});'


class InsertDataWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        assert len(context.instr.args) == 2
        assert instance_table in context.instr.args[0].regs
        data = context.instr.args[1]
        return f'WV_InsertData(&layer{context.recurse_context.layer_id}_inst->seq, {context.write_value(data)});'


class SeqReadyWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        assert sequence in context.value.regs
        return f'WV_SeqReady(&layer{context.instr_context.recurse_context.layer_id}_inst->seq)'


class SeqAssembleWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        layer_id = context.recurse_context.layer_id
        return f'layer{layer_id}_content = WV_SeqAssemble(&layer{layer_id}_inst->seq);'


class DestroyInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        return f'WV_DestroyInst(&runtime->tables[{context.recurse_context.layer_id}], ...);'
