from typing import List
from weaver.code import BasicBlock, Instr
from weaver.util import make_block


def write_all(blocks: List[BasicBlock], entry_id: int) -> str:
    blocks_text = ''
    for i, entry_block in enumerate(blocks):
        entry_block.group_aux.table_index = i
        for block in entry_block.recursive():
            blocks_text += write_block(block) + '\n\n'

    body_text = (
            'WV_U8 status = 0;\n'
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
    codes_text = '\n'.join(write_instr(instr) for instr in block.codes)
    if block.cond is None:
        codes_text += f'\ngoto {block.group_aux.callee_label()};'
    else:
        pass  # TODO
    return f'L{block.block_id}: {make_block(codes_text)}'


def write_instr(instr: Instr) -> str:
    text = '// ' + str(instr).replace('\n', '\n// ')

    return text