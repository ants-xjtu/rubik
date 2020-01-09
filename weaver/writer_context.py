from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional
from weaver.writer import ValueWriter, InstrWriter
from weaver.auxiliary import reg_aux, StructRegAux
from weaver.util import make_block
from weaver.code import Instr

if TYPE_CHECKING:
    from weaver.code import BasicBlock, Value, Reg
    from weaver.header import ParseAction, Struct


class GlobalContext:
    def __init__(self, next_table: Dict[Instr, BasicBlock]):
        # 0 is preserved for global exit
        self.next_index: Dict[Instr, int] = {instr: i + 1 for i, instr in enumerate(next_table.keys())}
        self.next_table = next_table
        self.text = ''
        self.required_header_types = set()

    def execute_block_recurse(self, entry_block: BasicBlock, layer_id: int, header_actions: List[ParseAction], inst_struct: Struct = None):
        context = BlockRecurseContext(
            self, entry_block, layer_id, header_actions, inst_struct)
        context.execute_header_action()
        for block in entry_block.recurse():
            context.execute_block(block)

    def append_text(self, text_part: str):
        if self.text:
            self.text += '\n'
        self.text += text_part

    def write_all(self, global_entry: BasicBlock) -> str:
        decl_text = '\n'.join(reg_aux.decl(reg_id) for reg_id, reg in reg_aux.regs.items() if
                              not reg.abstract and not isinstance(reg, StructRegAux))
        header_types_decl_text = '\n'.join(struct.create_aux().declare_type() for struct in self.required_header_types)
        body_text = (
            decl_text + '\n\n' +
            'WV_U8 status = 0;\n' +
            'WV_ByteSlice current = packet;\n'
            'WV_U8 ret_target = 0;\n'
            f'goto L{global_entry.block_id};\n\n' +
            self.text + '\n\n' +
            f'NI0_Ret: {make_block("return status;")}'
        )
        text = (
            '#include "weaver.h"\n\n' +
            header_types_decl_text + '\n\n'
            f'WV_U8 WV_ProcessPacket(WV_ByteSlice packet, WV_Runtime *runtime) {make_block(body_text)}'
        )
        return text

    def write_ret_switch(self) -> str:
        max_target = len(self.next_index) + 1
        targets_text = '\n'.join(f'case {index}: goto NI{index}_Ret;' for index in range(max_target))
        return f'switch (ret_target) {make_block(targets_text)}'


class BlockRecurseContext:
    def __init__(self, global_context: GlobalContext, entry_block: BasicBlock, layer_id: int,
                 actions: List[ParseAction], inst_struct: Optional[Struct]):
        self.global_context = global_context
        self.entry_block = entry_block
        self.layer_id = layer_id
        self.actions = actions
        self.struct_regs_owner: Dict[Reg, Struct] = {}
        self.inst_struct = inst_struct

    def execute_header_action(self):
        structs_decl = []
        for action in self.actions:
            for struct in action.iterate_structs():
                structs_decl.append(struct.create_aux().declare_type())
                self.struct_regs_owner.update({reg: struct for reg in struct.regs})
                self.global_context.required_header_types.add(struct)

    def execute_block(self, block: BasicBlock):
        text = f'L{block.block_id}: '
        codes_text = '\n'.join(
            InstrContext(self, block, instr).write() for instr in block.codes)
        if codes_text:
            codes_text += '\n'
        if block.cond is not None:
            assert block.yes_block is not None and block.no_block is not None
            codes_text += f'if ({InstrContext(self, block, Instr([], [], None)).write_value(block.cond)}) goto L{block.yes_block.block_id}; else goto L{block.no_block.block_id};'
        else:
            codes_text += self.global_context.write_ret_switch()
        self.global_context.append_text(text + make_block(codes_text))

    def content_name(self) -> str:
        return f'c{self.layer_id}'

    def prefetch_name(self) -> str:
        return f'f{self.layer_id}'

    def instance_key(self) -> str:
        return f'(WV_ByteSlice){{ .cursor = (WV_Byte *)&{self.key_struct.name()}, .length = {self.key_struct.sizeof()} }}'


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
