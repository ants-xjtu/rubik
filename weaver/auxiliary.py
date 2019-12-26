from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from weaver.code import BasicBlock


class BlockGroupAux:
    def __init__(self):
        self.callee_block: Optional[BasicBlock] = None
        self.table_index: Optional[int] = None

    def callee_label(self):
        if self.callee_block is None:
            return 'L_End'
        else:
            return f'L{self.callee_block.block_id}'

