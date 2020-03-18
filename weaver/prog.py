from weaver.compile2 import compile7_branch


class Expr:
    def __init__(self, read_regs, eval1_handler, compile6):
        self.read_regs = read_regs
        self.eval1_handler = eval1_handler
        self.compile6 = compile6

    def eval1(self, context):
        return self.eval1_handler.eval1(context)


class NotConstant(Exception):
    pass


class UpdateReg:
    def __init__(self, reg, expr, is_command, compile7):
        self.reg = reg
        self.expr = expr
        self.read_regs = expr.read_regs
        self.write_regs = {reg}
        self.is_command = is_command
        self.compile7 = compile7

    def eval2(self, context):
        if not self.is_command:
            try:
                context[self.reg] = self.expr.eval1(context)
            except NotConstant:
                pass


class Branch:
    def __init__(self, pred, yes_list, no_list):
        self.pred = pred
        self.yes_list = yes_list
        self.no_list = no_list
        self.read_regs = pred.read_regs
        self.write_regs = set()
        for instr in yes_list + no_list:
            self.read_regs |= instr.read_regs
            self.write_regs |= instr.write_regs
        self.is_command = False

    def eval2(self, context):
        try:
            if self.pred.eval1(context):
                for instr in self.yes_list:
                    instr.eval2(context)
            else:
                for instr in self.no_list:
                    instr.eval2(context)
        except NotConstant:
            pass

    @property
    def compile7(self):
        return compile7_branch(self)


class Block:
    count = 0

    def __init__(self, instr_list, pred, yes_block, no_block):
        self.instr_list = instr_list
        self.pred = pred
        self.yes_block = yes_block
        self.no_block = no_block

        self.block_id = Block.count
        Block.count += 1

    def recursive(self):
        yield self
        if self.pred is not None:
            yield from self.yes_block.recursive()
            yield from self.no_block.recursive()
