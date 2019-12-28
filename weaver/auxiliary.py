from __future__ import annotations
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from weaver.code import Reg


class RegTable:
    def __init__(self):
        self.regs: Dict[Reg, RegAux] = {}

    def __getitem__(self, reg: Reg):
        return self.regs[reg]

    count = 0

    def __setitem__(self, reg: Reg, aux: 'RegAux'):
        assert reg not in self.regs
        self.regs[reg] = aux
        self.count = max(self.count, reg + 1)

    def alloc(self, aux: 'RegAux') -> int:
        reg_id = self.count
        self[reg_id] = aux
        return reg_id

    def write(self, reg: Reg) -> str:
        return self[reg].value_name(reg)


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

    def value_name(self, reg: Reg) -> str:
        return f'_{reg}'


class StructRegAux(RegAux):
    def __init__(self, bit_len: int):
        super(StructRegAux, self).__init__(4, abstract=True)
        self.bit_len = bit_len
