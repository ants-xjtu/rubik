from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Set
from weaver.auxiliary import ValueAux, InstrAux
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


# def write_all(blocks: List[BasicBlock], entry_id: int) -> str:
#     blocks_text = ''
#     for i, entry_block in enumerate(blocks):
#         entry_block.group_aux.table_index = i
#     for entry_block in blocks:
#         for block in entry_block.recurse():
#             blocks_text += write_block(block) + '\n\n'
#
#     regs_decl = '\n'.join(aux.type_decl() + ' ' + f'_{reg_id};'
#                           for reg_id, aux in reg_aux.regs.items() if not aux.abstract)
#
#     body_text = (
#             'WV_U8 status = 0;\n\n' +
#             regs_decl + '\n\n' +
#             f'goto L{entry_id};\n' +
#             blocks_text +
#             f'L_End: {make_block("return status;")}'
#     )
#     text = (
#         '#include "weaver.h"\n\n'
#         f'WV_U8 WV_CONFIG_TABLE_COUNT = {len(blocks)};\n\n'
#         f'WV_U8 WV_ProcessPacket(WV_ByteSlice data, WV_Runtime *runtime) {make_block(body_text)}'
#     )
#     return text
#
#
# def write_block(block: BasicBlock) -> str:
#     for instr in block.codes:
#         instr.aux.block = block
#     codes_text = '\n'.join(write_instr(instr) for instr in block.codes)
#     if block.cond is None:
#         codes_text += f'\ngoto {block.group_aux.callee_label()};'
#     else:
#         pass  # TODO
#     return f'L{block.block_id}: {make_block(codes_text)}'
#
#
# def write_instr(instr: Instr) -> str:
#     text = '// ' + str(instr).replace('\n', '\n// ') + '\n'
#     if isinstance(instr, SetValue):
#         if isinstance(instr, Command):
#             # TODO
#             pass
#         else:
#             instr.value.aux.block = instr.aux.block
#             text += f'_{instr.reg} = {write_value(instr.value)};'
#     elif isinstance(instr, If):
#         for i in instr.yes + instr.no:
#             i.aux.block = instr.aux.block
#         text += f'if ({write_value(instr.cond)}) '
#         text += make_block('\n'.join(write_instr(i) for i in instr.yes))
#         text += ' else '
#         text += make_block('\n'.join(write_instr(i) for i in instr.no))
#     return text
#
#
# def write_value(value: Value) -> str:
#     if isinstance(value, AggValue):
#         values_text = [f'({write_value(v)})' for v in value.values]
#         return value.agg_aux.cexpr_template.format(*values_text)
#     else:
#         if isinstance(value.aux, InstValueAux):
#             return value.aux.write()
#         return value.aux.cexpr_template.format(*(f'_{reg}' for reg in value.regs))
