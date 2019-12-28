from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List
from weaver.writer import ValueWriter, InstrWriter
from weaver.auxiliary import reg_aux, StructRegAux
from weaver.util import make_block

if TYPE_CHECKING:
    from weaver.code import Instr, BasicBlock, Value
    from weaver.header import ParseAction, Struct


class GlobalContext:
    def __init__(self, next_table: Dict[Instr, BasicBlock]):
        self.next_table = next_table
        self.text = ''
        self.pre_text = ''
        # self.decl_structs

    def execute_block_recurse(self, entry_block: BasicBlock, layer_id: int, header_actions: List[ParseAction],
                              inst_struct: Struct = None):
        context = BlockRecurseContext(self, entry_block, layer_id, header_actions)
        if inst_struct is not None:
            self.pre_text += f'Layer{layer_id}_Inst *layer{layer_id}_inst, *layer{layer_id}_prefetch_inst;\n'
        self.pre_text += f'WV_ByteSlice layer{layer_id}_content;'
        context.execute_header_action()
        for block in entry_block.recurse():
            context.execute_block(block)

    def append_text(self, text_part: str):
        if self.text:
            self.text += '\n\n'
        self.text += text_part

    def append_pre_text(self, text_part: str):
        if self.pre_text:
            self.pre_text += '\n\n'
        self.pre_text += text_part

    def write_all(self, global_entry: BasicBlock, table_count: int) -> str:
        decl_text = '\n'.join(reg_aux.decl(reg_id) for reg_id, reg in reg_aux.regs.items() if
                              not reg.abstract and not isinstance(reg, StructRegAux))
        body_text = (
                'WV_U8 status = 0;\n\n' +
                decl_text + '\n\n' +
                self.pre_text + '\n\n' +
                'WV_ByteSlice current = packet;\n'
                f'goto L{global_entry.block_id};\n' +
                self.text + '\n\n' +
                f'L{global_entry.block_id}_Ret: {make_block("return status;")}'
        )
        text = (
            '#include "weaver.h"\n\n'
            f'WV_U8 WV_CONFIG_TABLE_COUNT = {table_count};\n\n'
            f'WV_U8 WV_ProcessPacket(WV_ByteSlice packet, WV_Runtime *runtime) {make_block(body_text)}'
        )
        return text


class BlockRecurseContext:
    def __init__(self, global_context: GlobalContext, entry_block: BasicBlock, layer_id: int,
                 actions: List[ParseAction]):
        self.global_context = global_context
        self.entry_block = entry_block
        self.layer_id = layer_id
        self.actions = actions
        self.struct_regs_owner = {}

    def execute_header_action(self):
        structs_decl = []
        for action in self.actions:
            for struct in action.iterate_structs():
                structs_decl.append("struct " + make_block(
                    '\n'.join(reg_aux.decl(reg) for reg in struct.regs)) + f' *_h{struct.struct_id};')
                self.struct_regs_owner.update({reg: struct for reg in struct.regs})
        self.global_context.append_pre_text('\n'.join(structs_decl))

    def execute_block(self, block: BasicBlock):
        text = f'L{block.block_id}: '
        codes_text = '\n'.join(
            InstrContext(self, block, instr).write() for instr in block.codes)
        if codes_text:
            codes_text += '\n'
        if block.cond is not None:
            codes_text += f'if ({InstrContext(self, block, None).write_value(block.cond)}) goto L{block.yes_block.block_id}; else goto L{block.no_block.block_id};'
        else:
            codes_text += f'goto L{self.entry_block.block_id}_Ret;'
        self.global_context.append_text(text + make_block(codes_text))


class InstrContext:
    def __init__(self, recurse_context: BlockRecurseContext, block: BasicBlock, instr: Instr):
        self.recurse_context = recurse_context
        self.block = block
        self.instr = instr

    def write(self) -> str:
        return (self.instr.aux or InstrWriter()).write(self)

    def write_instr(self, instr: Instr) -> str:
        return InstrContext(self.recurse_context, self.block, instr).write()

    def write_value(self, value: Value) -> str:
        return ValueContext(self, value).write()


class ValueContext:
    def __init__(self, instr_context: InstrContext, value: Value):
        self.instr_context = instr_context
        self.value = value

    def write(self) -> str:
        return (self.value.aux or ValueWriter()).write(self)

    def write_value(self, value: Value) -> str:
        return ValueContext(self.instr_context, value).write()
