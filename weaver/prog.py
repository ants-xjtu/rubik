from weaver.compile2 import compile7_branch


class Expr:
    def __init__(self, read_regs, eval1_handler, compile6, eval3_handler=None):
        self.read_regs = read_regs
        self.eval1_handler = eval1_handler
        self.compile6 = compile6
        self.eval3_handler = eval3_handler

    def eval1(self, context):
        return self.eval1_handler.eval1(context)

    def eval3(self, context):
        if self.eval3_handler is not None:
            self.eval3_handler(context)


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

    def preexpand(self):
        for index, instr in enumerate(self.instr_list):
            if isinstance(instr, Branch):
                if any(inner.is_command for inner in instr.yes_list + instr.no_list):
                    return Block(
                        self.instr_list[:index],
                        instr.pred,
                        Block(
                            instr.yes_list + self.instr_list[index + 1 :],
                            None,
                            None,
                            None,
                        ).preexpand(),
                        Block(
                            instr.no_list + self.instr_list[index + 1 :],
                            None,
                            None,
                            None,
                        ).preexpand(),
                    )
        return self

    def evaluate(self, context):
        if self.pred is None:
            return self
        original = dict(context)
        for instr in self.instr_list:
            instr.eval2(context)
        try:
            if self.pred.eval1(context):
                return Block(
                    self.instr_list + self.yes_block.instr_list,
                    self.yes_block.pred,
                    self.yes_block.yes_block,
                    self.yes_block.no_block,
                ).evaluate(original)
            else:
                return Block(
                    self.instr_list + self.no_block.instr_list,
                    self.no_block.pred,
                    self.no_block.yes_block,
                    self.no_block.no_block,
                ).evaluate(original)
        except NotConstant:
            pass
        yes_context = dict(context)
        self.pred.eval3(yes_context)
        yes_block = self.yes_block.evaluate(yes_context)
        no_block = self.no_block.evaluate(context)
        if yes_block is self.yes_block and no_block is self.no_block:
            return self
        else:
            return Block(self.instr_list, self.pred, yes_block, no_block)

    def optimize(self):
        return self.preexpand().evaluate({})
