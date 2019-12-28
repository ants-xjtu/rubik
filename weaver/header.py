from __future__ import annotations
from typing import List, TYPE_CHECKING, Dict
from weaver.auxiliary import reg_aux, StructRegAux
if TYPE_CHECKING:
    from weaver.code import Value, Reg


class Struct:
    count = 0

    def __init__(self, regs: List[Reg]):
        assert all(isinstance(reg_aux[reg], StructRegAux) for reg in regs)
        self.struct_id = self.count
        self.count += 1
        self.regs = regs


class ParseAction:
    pass


class LocateStruct(ParseAction):
    def __init__(self, struct: Struct):
        super(LocateStruct, self).__init__()
        self.struct = struct


class ParseByteSlice(ParseAction):
    def __init__(self, slice_reg: int):
        super(ParseByteSlice, self).__init__()
        self.slice_reg = slice_reg


class OptionalActions(ParseAction):
    def __init__(self, cond: Value, actions: List[ParseAction]):
        super(OptionalActions, self).__init__()
        self.cond = cond
        self.actions = actions


class TaggedParseLoop(ParseAction):
    def __init__(self, cond: Value, tag_bit_len: int, struct_map: Dict[int, Struct]):
        tag_max = 1 << tag_bit_len
        assert all(tag < tag_max for tag in struct_map)
        self.cond = cond
        self.tag_bit_len = tag_bit_len
        self.struct_map = struct_map
