from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weaver.code import Reg
    from weaver.header import Struct


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

    def value_name(self, reg: Reg):
        return f'_{reg}'


class StructRegAux(RegAux):
    def __init__(self, struct: Struct, bit_len: int):
        super(StructRegAux, self).__init__(4)
        self.struct = struct
        self.bit_len = bit_len
