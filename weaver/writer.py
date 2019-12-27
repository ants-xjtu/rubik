from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Set
from weaver.auxiliary import ValueAux, InstrAux, reg_aux
from weaver.util import make_block

if TYPE_CHECKING:
    from weaver.code import Instr, BasicBlock, Value


class GlobalContext:
    def __init__(self, next_table: Dict[Instr, BasicBlock]):
        self.next_table = next_table
        self.text = ''
        self.decl_regs: Set[int] = set()
        # self.decl_structs

    def execute_block_recurse(self, entry_block: BasicBlock, table_index: int):
        context = BlockRecurseContext(self, entry_block, table_index)
        for block in entry_block.recurse():
            context.execute_block(block)

    def append_text(self, text_part: str):
        if self.text:
            self.text += '\n\n'
        self.text += text_part

    def write_all(self, global_entry: BasicBlock, table_count: int) -> str:
        decl_text = '\n'.join(reg_aux[reg_id].type_decl() + ' ' + f'_{reg_id};'
                              for reg_id in self.decl_regs if not reg_aux[reg_id].abstract)
        body_text = (
                'WV_U8 status = 0;\n\n' +
                '// register declaration\n' +
                decl_text + '\n\n' +
                f'goto L{global_entry.block_id};\n' +
                self.text + '\n\n' +
                f'L_End: {make_block("return status;")}'
        )
        text = (
            '#include "weaver.h"\n\n'
            f'WV_U8 WV_CONFIG_TABLE_COUNT = {table_count};\n\n'
            f'WV_U8 WV_ProcessPacket(WV_ByteSlice data, WV_Runtime *runtime) {make_block(body_text)}'
        )
        return text


class BlockRecurseContext:
    def __init__(self, global_context: GlobalContext, entry_block: BasicBlock, table_index: int):
        self.global_context = global_context
        self.entry_block = entry_block
        self.table_index = table_index

    def execute_block(self, block: BasicBlock):
        text = f'L{block.block_id}: '
        codes_text = '\n'.join(
            InstrContext(self, block, instr).write() for instr in block.codes)
        self.global_context.append_text(text + make_block(codes_text))


class InstrContext:
    def __init__(self, recurse_context: BlockRecurseContext, block: BasicBlock, instr: Instr):
        self.recurse_context = recurse_context
        self.block = block
        self.instr = instr

    def write(self) -> str:
        return (self.instr.aux or InstrAux()).write(self)

    def write_instr(self, instr: Instr) -> str:
        return InstrContext(self.recurse_context, self.block, instr).write()

    def write_value(self, value: Value) -> str:
        return ValueContext(self, value).write()


class ValueContext:
    def __init__(self, instr_context: InstrContext, value: Value):
        self.instr_context = instr_context
        self.value = value

    def write(self) -> str:
        return (self.value.aux or ValueAux()).write(self)

    def write_value(self, value: Value) -> str:
        return ValueContext(self.instr_context, value).write()
