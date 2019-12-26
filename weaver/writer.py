from typing import List
from weaver.code import BasicBlock
from weaver.util import make_block


def write_all(blocks: List[BasicBlock], entry_id: int) -> str:
    text = \
        '#include "weaver.h"\n\n' \
        f'WV_I32 WV_ProcessPacket(WV_Byte *data, WV_U32 data_len, WV_Runtime *runtime) {make_block("return 0;")}'
    return text