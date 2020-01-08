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
        self.next_table = next_table
        self.text = ''
        self.pre_text = ''
        self.call_decl: Dict[str, str] = {}

    def execute_block_recurse(self, entry_block: BasicBlock, layer_id: int, header_actions: List[ParseAction], inst_struct: Struct = None):
        context = BlockRecurseContext(
            self, entry_block, layer_id, header_actions, inst_struct)
        self.append_pre_text(f'WV_ByteSlice {context.content_name()};')
        context.execute_header_action()
        for block in entry_block.recurse():
            context.execute_block(block)

    def append_text(self, text_part: str):
        if self.text:
            self.text += '\n'
        self.text += text_part

    def append_pre_text(self, text_part: str):
        if self.pre_text:
            self.pre_text += '\n'
        self.pre_text += text_part

    def insert_call_decl(self, name: str, decl: str):
        assert name not in self.call_decl or decl == self.call_decl[name]
        self.call_decl[name] = decl

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

    def write_template(self) -> str:
        return (
            '#include "weaver.h"\n\n' +
            '\n'.join(self.call_decl.values())
        )


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

        def execute_struct(s: Struct, extra: List[str] = None):
            fields = (extra or []) + [reg_aux.decl(reg) for reg in s.regs]
            if s.alloc:
                tail_text = f'{s.name()}_alloc, *{s.name()};\n{s.name()} = &{s.name()}_alloc;'
            else:
                tail_text = f'*{s.name()};'
            structs_decl.append(
                "struct " + make_block('\n'.join(fields)) + ' ' + tail_text)
            self.struct_regs_owner.update({reg: s for reg in s.regs})

        for action in self.actions:
            for struct in action.iterate_structs():
                execute_struct(struct)
        # TODO: BiInst
        if self.key_struct is not None:
            assert self.inst_struct is not None
            execute_struct(self.key_struct)
            execute_struct(self.inst_struct, extra=[
                           f'WV_INST_EXTRA_DECL({self.key_struct.sizeof()})'])
            structs_decl.append(
                f"WV_InstHeader({self.key_struct.sizeof()}) *{self.prefetch_name()};")
        self.global_context.append_pre_text('\n'.join(structs_decl))

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
            codes_text += f'goto L{self.entry_block.block_id}_Ret;'
        self.global_context.append_text(text + make_block(codes_text))

    def content_name(self) -> str:
        return f'c{self.layer_id}'

    def prefetch_name(self) -> str:
        return f'f{self.layer_id}'

    def instance_key(self) -> str:
        assert self.key_struct is not None
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
