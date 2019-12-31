from __future__ import annotations
from typing import List, TYPE_CHECKING, Dict, Generator
from weaver.auxiliary import reg_aux, StructRegAux

if TYPE_CHECKING:
    from weaver.code import Reg, Value


class Struct:
    count = 0

    def __init__(self, regs: List[Reg], alloc: bool = False):
        # assert all(isinstance(reg_aux[reg], StructRegAux) for reg in regs)
        self.struct_id = Struct.count
        Struct.count += 1
        self.regs: List[Reg] = regs
        self.byte_length = Struct.calculate_length(regs)
        self.alloc = alloc

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

    def name(self) -> str:
        return f'_h{self.struct_id}'

    def sizeof(self) -> str:
        return f'sizeof(*{self.name()})'


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
    def __init__(self, slice_reg: int):
        super(ParseByteSlice, self).__init__()
        self.slice_reg = slice_reg

    def iterate_structs(self) -> Generator[Struct, None, None]:
        pass


class OptionalActions(ParseAction):
    def __init__(self, cond: Value, actions: List[ParseAction]):
        super(OptionalActions, self).__init__()
        self.cond = cond
        self.actions = actions

    def iterate_structs(self) -> Generator[Struct, None, None]:
        for action in self.actions:
            yield from action.iterate_structs()


class TaggedParseLoop(ParseAction):
    def __init__(self, cond: Value, tag: Reg, struct_map: Dict[int, Struct]):
        tag_max = 1 << reg_aux[tag].byte_len
        assert all(tag < tag_max for tag in struct_map)
        self.cond = cond
        self.tag = tag
        self.struct_map = struct_map

    def iterate_structs(self) -> Generator[Struct, None, None]:
        yield from self.struct_map.values()
