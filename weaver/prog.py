from __future__ import annotations

# pylint: disable = unused-wildcard-import
from typing import *
from weaver.compile2 import compile7_branch


class Expr:
    def __init__(self, read_regs, eval1_handler, compile6, eval3_handler=None):
        assert isinstance(read_regs, set)
        self.read_regs = read_regs
        self.eval1_handler = eval1_handler
        self.compile6 = compile6
        self.eval3_handler = eval3_handler

    def eval1(self, context):
        return self.eval1_handler.eval1(context)

    def eval3(self, context):
        if self.eval3_handler is not None:
            self.eval3_handler.eval3(context)


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
        self.is_choice = False

    def eval2(self, context):
        if not self.is_command:
            try:
                context[self.reg] = self.expr.eval1(context)
            except NotConstant:
                pass


class Branch:
    def __init__(self, pred, yes_list, no_list, is_choice=False):
        self.pred = pred
        self.yes_list = yes_list
        self.no_list = no_list
        self.read_regs = pred.read_regs
        self.write_regs = set()
        for instr in yes_list + no_list:
            self.read_regs |= instr.read_regs
            self.write_regs |= instr.write_regs
        self.is_command = False
        self.is_choice = is_choice

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


Reg = int
Env = Dict[Reg, Any]


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

    @staticmethod
    def build_dep_graph(
        codes: List[UpdateReg], cond: Expr = None
    ) -> Dict[Union[UpdateReg, Expr], Set[UpdateReg]]:
        dep_graph: Dict[Union[UpdateReg, Expr], Set[UpdateReg]] = {}
        # all instructions that (possibly) processes the last writing to a register,
        # and all instructions that read the register after the last writing
        reg_graph: Dict[Reg, Tuple[List[UpdateReg], List[UpdateReg]]] = {}
        for instr in cast(List[UpdateReg], codes):
            dep_graph[instr] = set()
            for write_reg in instr.write_regs:
                # the writing must be after all the readings which expect the old value
                # the writing also must be after the previous writing to prevent to store wrong value eventually
                if write_reg in reg_graph:
                    all_write, all_read = reg_graph[write_reg]
                    dep_graph[instr].update(all_write)
                    dep_graph[instr].update(all_read)
            # the reading must be after any writing
            for read_reg in instr.read_regs:
                if read_reg in reg_graph and reg_graph[read_reg][0] is not None:
                    dep_graph[instr].update(reg_graph[read_reg][0])

            # update register graph with current instruction
            # the readings are appended
            for read_reg in instr.read_regs:
                if read_reg not in reg_graph:
                    reg_graph[read_reg] = [], []
                reg_graph[read_reg][1].append(instr)
            for write_reg in instr.write_regs:
                if isinstance(instr, Branch):
                    # if the writing happens, the instruction becomes the one performs the last writing
                    # otherwise `write_reg` is untouched
                    if write_reg not in reg_graph:
                        reg_graph[write_reg] = [], []
                    reg_graph[write_reg][0].append(instr)
                else:
                    # the writing clears all reading if exist
                    reg_graph[write_reg] = [instr], []

        if cond is not None:
            dep_graph[cond] = set()
            for read_reg in cond.read_regs:
                if read_reg in reg_graph and reg_graph[read_reg][0] is not None:
                    dep_graph[cond].update(reg_graph[read_reg][0])
        return dep_graph

    @staticmethod
    def scan_codes(
        codes: List[UpdateReg], agg_choice: Expr = None
    ) -> Tuple[List[UpdateReg], bool]:
        choice = False
        agg_choice = agg_choice or Expr(set(), None, None)
        dep_graph = Block.build_dep_graph(codes, agg_choice)
        scanned: List[Optional[UpdateReg]] = [None] * len(codes)
        choice_instr = {instr: instr in dep_graph[agg_choice] for instr in codes}
        for i in (j - 1 for j in range(len(codes), 0, -1)):
            instr = codes[i]
            if instr.is_command:
                choice = True
                agg_choice = Expr(agg_choice.read_regs | instr.read_regs, None, None)
            if isinstance(instr, Branch):
                scanned_yes, choice_yes = Block.scan_codes(instr.yes_list, agg_choice)
                scanned_no, choice_no = Block.scan_codes(instr.no_list, agg_choice)
                if choice_yes or choice_no:
                    choice = True
                    agg_choice = Expr(
                        agg_choice.read_regs | instr.read_regs, None, None
                    )
                if choice_yes or choice_no or choice_instr[instr]:
                    for dep_instr in dep_graph[instr]:
                        choice_instr[dep_instr] = True
                    scanned[i] = Branch(instr.pred, scanned_yes, scanned_no, True)
                else:
                    scanned[i] = instr
            else:
                if choice_instr[instr]:
                    for dep_instr in dep_graph[instr]:
                        choice_instr[dep_instr] = True
                scanned[i] = instr
        assert all(instr is not None for instr in scanned)
        return cast(List[UpdateReg], scanned), choice

    @staticmethod
    def from_codes(codes: List[UpdateReg]) -> Block:
        # for instr in codes:
        #     print(instr)
        # print()
        scanned, _ = Block.scan_codes(codes)
        return Block(scanned, None, None, None)

    def eval_reduce(self, consts: Env = None) -> Block:
        consts = cast(Env, consts or {})
        affected_consts = dict(consts)
        for i, instr in enumerate(self.instr_list):
            if isinstance(instr, Branch):
                prev_codes = self.instr_list[:i]
                after_codes = self.instr_list[i + 1 :]
                try:
                    choice_cond = instr.pred.eval1(affected_consts)
                except NotConstant:
                    choice_cond = None
                if choice_cond is not None:
                    if choice_cond:
                        codes = prev_codes + instr.yes_list + after_codes
                    else:
                        codes = prev_codes + instr.no_list + after_codes
                    return Block(
                        codes, self.pred, self.yes_block, self.no_block
                    ).eval_reduce(consts)
                elif instr.is_choice:
                    # beg for this not too heavy
                    codes = prev_codes
                    cond = instr.pred
                    yes_block = Block(
                        instr.yes_list + after_codes,
                        self.pred,
                        self.yes_block,
                        self.no_block,
                    )
                    no_block = Block(
                        instr.no_list + after_codes,
                        self.pred,
                        self.yes_block,
                        self.no_block,
                    )
                    return Block(codes, cond, yes_block, no_block).eval_reduce(consts)
            instr.eval2(affected_consts)
        if self.pred is None:
            return self
        assert self.yes_block is not None and self.no_block is not None
        try:
            cond_value = self.pred.eval1(affected_consts)
        except NotConstant:
            cond_value = None
        if cond_value is not None:
            if cond_value:
                selected_block = self.no_block.eval_reduce(affected_consts)
            else:
                selected_block = self.yes_block.eval_reduce(affected_consts)
            return Block(
                self.instr_list + selected_block.instr_list,
                selected_block.pred,
                selected_block.yes_block,
                selected_block.no_block,
            )
        else:
            yes_consts = dict(affected_consts)
            self.pred.eval3(yes_consts)
            yes_block = self.yes_block.eval_reduce(yes_consts)
            no_block = self.no_block.eval_reduce(affected_consts)
            if yes_block is self.yes_block and no_block is self.no_block:
                return self
            return Block(self.instr_list, self.pred, yes_block, no_block)

    def __str__(self):
        label_line = f"L{self.block_id}:\n"
        code_lines = [str(instr) for instr in self.instr_list]
        if self.pred is not None:
            code_lines.append(
                f"Goto Branch {self.pred} L{self.yes_block.block_id} Else L{self.no_block.block_id}"
            )
        if not code_lines:
            code_lines = ["Nop"]
        return label_line + "\n".join(code_lines)

    def recurse(self) -> Generator[Block, None, None]:
        yield self
        if self.pred is not None:
            assert self.yes_block is not None and self.no_block is not None
            yield from self.yes_block.recurse()
            yield from self.no_block.recurse()

    def proc_exit(self, proc) -> Block:
        if self.pred is None:
            return Block(proc(self.instr_list), None, None, None)
        else:
            return Block(
                self.instr_list,
                self.pred,
                self.yes_block.proc_exit(proc),
                self.no_block.proc_exit(proc),
            )

    class IfDep(Exception):
        def __init__(self, i, instr):
            super().__init__()
            self.i = i
            self.instr = instr

    def build_fixed(self) -> List[bool]:
        fixed = [False] * len(self.instr_list)
        assert self.pred is not None
        read_regs = set(self.pred.read_regs)
        write_regs: Set[Reg] = set()
        command_write: Set[Reg] = set()
        for i in (j - 1 for j in range(len(self.instr_list), 0, -1)):
            instr = self.instr_list[i]
            instr_read = set(instr.read_regs)
            instr_write = set(instr.write_regs)
            if (
                instr_write & read_regs
                or instr_read & write_regs
                or instr_write & write_regs
            ):
                if not instr_read & command_write and isinstance(instr, Branch):
                    raise Block.IfDep(i, instr)
                fixed[i] = True
                read_regs.update(instr.read_regs)
                write_regs.update(instr.write_regs)
                # if isinstance(instr, UpdateReg):
                #     read_regs.discard(instr.reg)
                if instr.is_command:
                    command_write.update(instr.write_regs)
            # else:
            #     if isinstance(instr, UpdateReg):
            #         write_regs.discard(instr.reg)
        return fixed

    def relocate_cond(self) -> Block:
        if self.pred is None:
            return self
        assert self.yes_block is not None and self.no_block is not None

        try:
            fixed = self.build_fixed()
        except Block.IfDep as if_dep:
            i, instr = if_dep.i, if_dep.instr
            # condition is blocked by (at least) one Branch
            # expand this Branch may remove the blocker to some extent
            # note: there's a little duplicated work here
            codes = self.instr_list[:i]
            cond = instr.pred
            rest_codes = self.instr_list[i + 1 :]
            yes_block = Block(
                instr.yes_list + rest_codes, self.pred, self.yes_block, self.no_block
            )
            no_block = Block(
                instr.no_list + rest_codes, self.pred, self.yes_block, self.no_block
            )
            return Block(codes, cond, yes_block, no_block).relocate_cond()

        # except Block.IfDep:
        #     # after preprocess in scan_codes, there should be no dependent Branch exists
        #     raise

        fixed_codes = [instr for i, instr in enumerate(self.instr_list) if fixed[i]]
        shifted_codes = [
            instr for i, instr in enumerate(self.instr_list) if not fixed[i]
        ]
        if shifted_codes:
            yes_block = Block(
                shifted_codes + self.yes_block.instr_list,
                self.yes_block.pred,
                self.yes_block.yes_block,
                self.yes_block.no_block,
            ).relocate_cond()
            no_block = Block(
                shifted_codes + self.no_block.instr_list,
                self.no_block.pred,
                self.no_block.yes_block,
                self.no_block.no_block,
            ).relocate_cond()
        else:
            yes_block = self.yes_block.relocate_cond()
            no_block = self.no_block.relocate_cond()
        if yes_block is self.yes_block and no_block is self.no_block:
            return self
        return Block(fixed_codes, self.pred, yes_block, no_block)

    def optimize(self, proc=None) -> Block:
        block = self
        while True:
            opt_block = block.eval_reduce().relocate_cond()
            if opt_block is block:
                return block
            if proc is None:
                block = opt_block
            else:
                block = opt_block.proc_exit(proc)
