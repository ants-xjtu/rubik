from __future__ import annotations
from weaver.code import *
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weaver.writer import InstrContext, ValueContext


class RegTable:
    def __init__(self):
        self.regs = {}

    def __getitem__(self, reg: int):
        return self.regs[reg]

    count = 0

    def __setitem__(self, reg: int, aux: 'RegAux'):
        assert reg not in self.regs
        self.regs[reg] = aux
        self.count = max(self.count, reg + 1)

    def alloc(self, aux: 'RegAux') -> int:
        reg_id = self.count
        self[reg_id] = aux
        return reg_id


reg_aux = RegTable()


class RegAux:
    def __init__(self, byte_len: int = None, abstract: bool = False):
        if byte_len is not None:
            assert byte_len in {1, 2, 4, 8}
        self.byte_len = byte_len
        self.abstract = abstract

    def type_decl(self) -> str:
        assert not self.abstract
        if self.byte_len is not None:
            return f'WV_U{self.byte_len * 8}'
        else:
            return 'WV_ByteSlice'


class ValueAux:
    # fallback
    def write(self, context: ValueContext) -> str:
        if isinstance(context.value, AggValue):
            return AggValueAux(context.value.agg_eval).write(context)
        else:
            return TemplateValueAux(context.value.eval_template).write(context)


class TemplateValueAux(ValueAux):
    def __init__(self, cexpr_template: str):
        self.cexpr_template = cexpr_template

    def write(self, context: ValueContext) -> str:
        return self.cexpr_template.format(*(f'_{reg}' for reg in context.value.regs))


class AggValueAux(ValueAux):
    def __init__(self, cexpr_template: str):
        super().__init__()
        self.cexpr_template = cexpr_template

    def write(self, context: ValueContext) -> str:
        assert isinstance(context.value, AggValue)
        values_text = ('(' + context.write_value(value) + ')' for value in context.value.values)
        return self.cexpr_template.format(*values_text)


class InstValueAux(ValueAux):
    def __init__(self, key):
        self.key = key

    def write(self, context: ValueContext) -> str:
        return f'table_{context.instr_context.recurse_context.table_index}_inst->{self.key}'


class InstrAux:
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
