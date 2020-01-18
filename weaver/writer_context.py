from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional
from weaver.writer import ValueWriter, InstrWriter
from weaver.auxiliary import reg_aux, StructRegAux, DataStructAux, BiDataStructAux
from weaver.util import make_block
from weaver.code import Instr, Value
from weaver.lang import Seq

if TYPE_CHECKING:
    from weaver.code import BasicBlock, Value, Reg
    from weaver.header import ParseAction, Struct


class GlobalContext:
    def __init__(self, next_table: Dict[Instr, BasicBlock]):
        self.next_table = next_table
        self.text = ''
        self.required_headers = set()
        self.required_calls = {}
        self.required_inst = {}
        self.required_return_blocks = set()
        self.layer_count = 0
        self.recurse_contexts = []
        self.struct_regs_owner = {}

    def execute_block_recurse(self,
                              entry_block: BasicBlock,
                              header_actions: List[ParseAction],
                              inst_struct: Struct = None,
                              seq: Seq = None,
                              use_data: bool = True,
                              ):
        layer_id = self.layer_count
        self.layer_count += 1
        if inst_struct is not None:
            self.required_inst[layer_id] = inst_struct
        bidirection = inst_struct is not None and isinstance(
            inst_struct.create_aux(), BiDataStructAux)
        context = BlockRecurseContext(
            self, entry_block, layer_id, header_actions, inst_struct, bidirection, seq, use_data)
        context.execute_header_action()
        context.execute_inst_struct()
        self.recurse_contexts.append(context)

    def append_text(self, text_part: str):
        if self.text:
            self.text += '\n'
        self.text += text_part

    def execute_all(self):
        for context in self.recurse_contexts:
            context.execute_all()

    def write_all(self, global_entry: BasicBlock) -> str:
        return (
            '#include <weaver.h>\n' +
            '#include <tommyds/tommyhashdyn.h>\n\n' +
            '#if TOMMY_SIZE_BIT == 64\n' +
            '#define hash(k, s) tommy_hash_u64(0, k, s)\n' +
            '#else\n' +
            '#define hash(k, s) tommy_hash_u32(0, k, s)\n' +
            '#endif\n\n' +
            self.write_extern_calls_decl() + '\n\n' +
            self.write_header_types_decl() + '\n\n' +
            self.write_inst_types_decl() + '\n\n' +
            self.write_eq_funcs() + '\n\n' +
            self.write_runtime_impl() + '\n\n' +
            f'WV_U8 WV_ProcessPacket(WV_ByteSlice packet, WV_Runtime *runtime) ' + make_block(
                GlobalContext.write_regs() + '\n\n' +
                self.write_header_vars() + '\n\n' +
                self.write_inst_decl() + '\n\n' +
                self.write_content_vars() + '\n\n' +
                'WV_U8 status = 0;\n' +
                'WV_ByteSlice current = packet, saved;\n' +
                self.write_return_vars() + '\n' +
                'WV_I32 ret_target = -1;\n'
                f'goto L{global_entry.block_id};\n\n' +
                self.text + '\n\n' +
                self.write_shower() + '\n\n'
                f'GlobalExit: {make_block(self.write_finalize_block())}'
            )
        )

    def write_finalize_block(self):
        return '\n'.join([f'if (nf{i}) free(nf{i});' for i in range(self.layer_count)] + ['return status;'])

    def write_header_types_decl(self) -> str:
        return '\n'.join(
            struct.create_aux().declare_type() for struct in self.required_headers)

    def write_inst_types_decl(self) -> str:
        return '\n'.join(struct.create_aux().declare_inst_type(lid) for lid, struct in self.required_inst.items())

    def write_inst_decl(self) -> str:
        return '\n'.join(
            f'L{lid}_Fetch *f{lid};\n'
            f'{struct.create_aux().declare_pointer()}'
            for lid, struct in self.required_inst.items())

    def write_content_vars(self) -> str:
        return '\n'.join(f'WV_ByteSlice c{i} = WV_EMPTY;\nWV_Byte *nf{i} = NULL;' for i in range(self.layer_count))

    def write_return_vars(self) -> str:
        return '\n'.join(f'WV_I32 saved_target_{block.block_id};' for block in self.required_return_blocks)

    @staticmethod
    def write_regs() -> str:
        return '\n'.join(reg_aux.decl(reg_id) for reg_id, reg in reg_aux.regs.items() if
                         not reg.abstract and not isinstance(reg, StructRegAux))

    def write_header_vars(self) -> str:
        return '\n'.join(
            struct.create_aux().declare_pointer() + '\n' +
            f'WV_U8 {struct.create_aux().parse_flag()} = 0;'
            for struct in self.required_headers)

    def write_shower(self) -> str:
        targets_text = (
            '\n'.join(
                f'case {block.block_id}: goto NI{block.block_id}_Ret;' for block in self.required_return_blocks)
            + '\ndefault: goto GlobalExit;')
        return 'L_Shower: ' + make_block(f'switch (ret_target) {make_block(targets_text)}')

    def write_extern_calls_decl(self) -> str:
        return '\n'.join(
            f'extern WV_U8 {name}({", ".join(reg_aux[reg].type_decl() for reg in regs)});' for name, regs in self.required_calls.items())

    def write_eq_funcs(self) -> str:
        return '\n'.join(
            f'int {GlobalContext.eq_func_name(lid)}(const void *key, const void *object) ' + make_block(
                f'return memcmp(key, object, sizeof({GlobalContext.key_struct_name(lid)}));'
            )
            for lid, struct in self.required_inst.items())

    @staticmethod
    def eq_func_name(layer_id) -> str:
        return f'l{layer_id}_eq'

    @staticmethod
    def key_struct_name(layer_id) -> str:
        return DataStructAux.key_struct_type(layer_id)

    def write_runtime_impl(self) -> str:
        runtime_struct = 'struct _WV_Runtime ' + make_block('\n'.join([
            'WV_Profile profile;',
        ] + [
            f'{struct.create_aux().typedef()} *{GlobalContext.prealloc(lid)};'
            for lid, struct in self.required_inst.items()
        ] + [
            f'tommy_hashdyn hash_{lid};' for lid in self.required_inst.keys()
        ])) + ';'
        alloc_runtime = 'WV_Runtime *WV_AllocRuntime() ' + make_block('\n'.join([
            'WV_Runtime *rt = malloc(sizeof(WV_Runtime));',
            *[
                f'tommy_hashdyn_init(&rt->hash_{lid});\n' +
                f'rt->{GlobalContext.prealloc(lid)} = malloc(sizeof({struct.create_aux().typedef()}));\n' +
                f'memset(rt->{GlobalContext.prealloc(lid)}, 0, sizeof({struct.create_aux().typedef()}));'
                for lid, struct in self.required_inst.items()
            ],
            'return rt;',
        ]))
        free_runtime = 'WV_U8 WV_FreeRuntime(WV_Runtime *rt) ' + make_block('\n'.join([
            *[
                # TODO: free instances in table
                f'tommy_hashdyn_done(&rt->hash_{lid});\n' +
                f'free(rt->{GlobalContext.prealloc(lid)});'
                for lid, struct in self.required_inst.items()
            ],
            'free(rt);',
            'return 0;',
        ]))
        get_profile = 'WV_Profile *WV_GetProfile(WV_Runtime *rt) ' + make_block('\n'.join([
            'return &rt->profile;'
        ]))
        return '\n'.join([runtime_struct, alloc_runtime, free_runtime, get_profile])

    def write_template(self) -> str:
        text = '#include "weaver.h"'
        for name, regs in self.required_calls.items():
            if regs == []:
                call_text = f'WV_U8 {name}() '
            else:
                call_text = f'WV_U8 {name}('
                for reg in regs:
                    call_text += f'\n  {reg_aux[reg].type_decl()} _{reg},'
                call_text = call_text[:-1]  # eat postfix comma
                call_text += '\n) '
            call_text += make_block('return 0;')
            text += '\n\n' + call_text
        return text

    @staticmethod
    def prealloc(layer_id) -> str:
        return f'prealloc_{layer_id}'


class BlockRecurseContext:
    def __init__(self, global_context: GlobalContext, entry_block: BasicBlock, layer_id: int,
                 actions: List[ParseAction], inst_struct: Optional[Struct], bidirection: bool, seq: Optional[Seq], use_data: bool):
        self.global_context = global_context
        self.entry_block = entry_block
        self.layer_id = layer_id
        self.actions = actions
        self.inst_struct = inst_struct
        self.bidirection = bidirection
        self.seq = seq
        self.use_data = Value([], str(int(use_data)))

    def execute_header_action(self):
        structs_decl = []
        for action in self.actions:
            for struct in action.iterate_structs():
                structs_decl.append(struct.create_aux().declare_type())
                self.global_context.struct_regs_owner.update(
                    {reg: struct for reg in struct.regs})
                self.global_context.required_headers.add(struct)

    def execute_inst_struct(self):
        if self.inst_struct is not None:
            self.global_context.struct_regs_owner.update(
                {reg: self.inst_struct for reg in self.inst_struct.regs})

    def execute_block(self, block: BasicBlock):
        text = f'L{block.block_id}: '
        # print(block)
        codes_text = '\n'.join(
            InstrContext(self, block, instr).write() for instr in block.codes)
        if codes_text:
            codes_text += '\n'
        if block.cond is not None:
            assert block.yes_block is not None and block.no_block is not None
            codes_text += f'if ({InstrContext(self, block, Instr([], [], None)).write_value(block.cond)}) goto L{block.yes_block.block_id}; else goto L{block.no_block.block_id};'
        else:
            codes_text += 'goto L_Shower;'
        self.global_context.append_text(text + make_block(codes_text))

    def execute_all(self):
        for block in self.entry_block.recurse():
            self.execute_block(block)

    def content_name(self) -> str:
        return f'c{self.layer_id}'

    def prefetch_name(self) -> str:
        return f'f{self.layer_id}'

    def eq_func_name(self) -> str:
        return GlobalContext.eq_func_name(self.layer_id)

    def key_struct_size(self) -> str:
        return f'sizeof({GlobalContext.key_struct_name(self.layer_id)})'

    def prealloc(self) -> str:
        return GlobalContext.prealloc(self.layer_id)


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
