from __future__ import annotations
from typing import List, TYPE_CHECKING, Dict, Generator
from weaver.auxiliary import reg_aux, StructRegAux
from weaver.util import make_block

if TYPE_CHECKING:
    from weaver.code import Reg, Value


class Struct:
    count = 0

    def __init__(self, regs: List[Reg], aux_creator):
        # assert all(isinstance(reg_aux[reg], StructRegAux) for reg in regs)
        self.struct_id = Struct.count
        Struct.count += 1
        self.regs: List[Reg] = regs
        self.byte_length = Struct.calculate_length(regs)
        self.aux_creator = aux_creator

    @staticmethod
    def calculate_length(regs: List[Reg]) -> int:
        bit_length = 0
        for reg in (reg_aux[reg_id] for reg_id in regs):
            assert isinstance(reg, StructRegAux)
            assert reg.byte_len is not None
            if reg.bit_len is not None:
                bit_length += reg.bit_len
            else:
                assert bit_length % 8 == 0
                bit_length += reg.byte_len * 8
        assert bit_length % 8 == 0
        return bit_length // 8

    def create_aux(self):
        return self.aux_creator(self)


class ParseAction:
    def iterate_structs(self) -> Generator[Struct, None, None]:
        raise NotImplementedError()


class LocateStruct(ParseAction):
    def __init__(self, struct: Struct):
        super(LocateStruct, self).__init__()
        self.struct = struct

    def iterate_structs(self) -> Generator[Struct, None, None]:
        yield self.struct


class ParseByteSlice(ParseAction):
    def __init__(self, slice_reg: Reg, byte_length: Value):
        super(ParseByteSlice, self).__init__()
        self.slice_reg = slice_reg
        self.byte_length = byte_length

    def iterate_structs(self) -> Generator[Struct, None, None]:
        yield from []


class OptionalActions(ParseAction):
    def __init__(self, cond: Value, actions: List[ParseAction]):
        super(OptionalActions, self).__init__()
        self.cond = cond
        self.actions = actions

    def iterate_structs(self) -> Generator[Struct, None, None]:
        for action in self.actions:
            yield from action.iterate_structs()


class TaggedParseLoop(ParseAction):
    def __init__(self, cond: Value, tag: Reg, action_map: Dict[int, List[ParseAction]]):
        tag_max = 1 << (reg_aux[tag].byte_len * 8)
        assert all(tag < tag_max for tag in action_map if tag is not None)
        self.cond = cond
        self.tag = tag
        self.action_map = action_map

    def iterate_structs(self) -> Generator[Struct, None, None]:
        for actions in self.action_map.values():
            for action in actions:
                yield from action.iterate_structs()
