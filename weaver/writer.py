from typing import List
from weaver.code import BasicBlock
from weaver.util import make_block


def write_all(blocks: List[BasicBlock], entry_id: int) -> str:
    blocks_text = ''
    for entry_block in blocks:
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
        f'WV_U8 WV_ProcessPacket(WV_Byte *data, WV_U32 data_len, WV_Runtime *runtime) {make_block(body_text)}'
    )
    return text


def write_block(block: BasicBlock) -> str:
    codes_text = ''
    return f'L{block.block_id}: {make_block(codes_text)}'
