from typing import List
from weaver.code import *
from weaver.util import make_block
from weaver.auxiliary import *


def write_all(blocks: List[BasicBlock], entry_id: int) -> str:
    blocks_text = ''
    for i, entry_block in enumerate(blocks):
        entry_block.group_aux.table_index = i
    for entry_block in blocks:
        for block in entry_block.recursive():
            blocks_text += write_block(block) + '\n\n'

    regs_decl = '\n'.join(aux.type_decl() + ' ' + f'_{reg_id};'
                          for reg_id, aux in reg_aux.regs.items() if not aux.abstract)

    body_text = (
            'WV_U8 status = 0;\n\n' +
            regs_decl + '\n\n' +
            f'goto L{entry_id};\n' +
            blocks_text +
            f'L_End: {make_block("return status;")}'
    )
    text = (
        '#include "weaver.h"\n\n'
        f'WV_U8 WV_CONFIG_TABLE_COUNT = {len(blocks)};\n\n'
        f'WV_U8 WV_ProcessPacket(WV_ByteSlice data, WV_Runtime *runtime) {make_block(body_text)}'
    )
    return text


def write_block(block: BasicBlock) -> str:
    for instr in block.codes:
        instr.aux.block = block
    codes_text = '\n'.join(write_instr(instr) for instr in block.codes)
    if block.cond is None:
        codes_text += f'\ngoto {block.group_aux.callee_label()};'
    else:
        pass  # TODO
    return f'L{block.block_id}: {make_block(codes_text)}'


def write_instr(instr: Instr) -> str:
    text = '// ' + str(instr).replace('\n', '\n// ') + '\n'
    if isinstance(instr, SetValue):
        if isinstance(instr, Command):
            # TODO
            pass
        else:
            instr.value.aux.block = instr.aux.block
            text += f'_{instr.reg} = {write_value(instr.value)};'
    elif isinstance(instr, If):
        for i in instr.yes + instr.no:
            i.aux.block = instr.aux.block
        text += f'if ({write_value(instr.cond)}) '
        text += make_block('\n'.join(write_instr(i) for i in instr.yes))
        text += ' else '
        text += make_block('\n'.join(write_instr(i) for i in instr.no))
    return text


def write_value(value: Value) -> str:
    if isinstance(value, AggValue):
        values_text = [f'({write_value(v)})' for v in value.values]
        return value.agg_aux.cexpr_template.format(*values_text)
    else:
        if isinstance(value.aux, InstValueAux):
            return value.aux.write()
        return value.aux.cexpr_template.format(*(f'_{reg}' for reg in value.regs))
