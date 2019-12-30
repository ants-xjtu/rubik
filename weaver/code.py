from __future__ import annotations
from typing import *
from weaver.util import make_block

if TYPE_CHECKING:
    from weaver.writer import ValueWriter, InstrWriter

Reg = int
Env = Dict[Reg, Any]


class Instr:
    def __init__(self, read_regs: List[Reg], write_regs: List[Reg], aux: Optional[InstrWriter]):
        self.read_regs = read_regs
        self.write_regs = write_regs
        self.aux = aux

    def affect(self, env: Env) -> Env:
        raise NotImplementedError()


class SetValue(Instr):
    def __init__(self, reg: Reg, value: Value, aux: InstrWriter = None):
        super(SetValue, self).__init__(value.regs, [reg], aux)
        self.reg = reg
        self.value = value

    def __str__(self):
        return f'${self.reg} = {self.value}'

    def affect(self, env: Env) -> Env:
        reg_value = self.value.try_eval(env)
        if reg_value is not None:
            env[self.reg] = reg_value
        return env


class Command(SetValue):
    def __init__(self, provider: Reg, name: str, args: List[Value], opt_target: bool = False,
                 aux: InstrWriter = None):
        super(Command, self).__init__(provider, AggValue(args), aux)
        self.provider = provider
        self.name = name
        self.args = args
        self.opt_target = opt_target

    def __str__(self):
        args_str = ', '.join(str(arg) for arg in self.args)
        return f'${self.provider}->{self.name}({args_str})'

    def affect(self, env: Env) -> Env:
        return env


class If(Instr):
    def __init__(self, cond: Value, yes: List[Instr], no: List[Instr] = None):
        self.cond = cond
        self.yes = yes
        self.no = no or []

        read_regs = set(cond.regs)
        write_regs = set()
        for instr in self.yes + self.no:
            read_regs.update(instr.read_regs)
            write_regs.update(instr.write_regs)
        super(If, self).__init__(list(read_regs), list(write_regs), None)

    def affect(self, env: Env) -> Env:
        cond_value = self.cond.try_eval(env)
        if cond_value is not None:
            if cond_value == 0:
                for instr in self.no:
                    env = instr.affect(env)
            else:
                for instr in self.yes:
                    env = instr.affect(env)
            return env

        yes_env = dict(env)
        if isinstance(self.cond, EqualTest):
            yes_env[self.cond.equal_reg] = self.cond.equal_value
        for instr in self.yes:
            yes_env = instr.affect(yes_env)
        no_env = dict(env)
        for instr in self.no:
            no_env = instr.affect(no_env)
        return {reg: yes_env[reg] for reg in yes_env.keys() & no_env.keys()}

    def __str__(self):
        return f'If {self.cond} Do /* {len(self.yes)} code(s) */ Else /* {len(self.no)} code(s) */'


class Choice(If):
    def __init__(self, cond: Value, yes: List[Instr], no: List[Instr]):
        super().__init__(cond, yes, no)

    def __str__(self):
        yes_str = '\n'.join(str(instr) for instr in self.yes)
        no_str = '\n'.join(str(instr) for instr in self.no)
        return f'Choice {self.cond} {make_block(yes_str)} Else {make_block(no_str)}'


class Value:
    def __init__(self, regs: List[Reg], eval_template: str = '<should not evaluate>', aux: ValueWriter = None):
        self.regs = regs
        self.aux: Optional[ValueWriter] = aux
        self.eval_template = eval_template

    def __str__(self):
        return self.eval_template.format(*(f'${reg}' for reg in self.regs))

    def try_eval(self, consts: Env) -> Optional[Any]:
        reg_values = []
        for reg in self.regs:
            if reg not in consts:
                return None
            reg_values.append(consts[reg])
        return eval(self.eval_template.format(*reg_values))


class AggValue(Value):
    def __init__(self, values: List[Value], agg_template: str = '<should not evaluate>', aux: ValueWriter = None):
        super().__init__(list(set(sum((value.regs for value in values), []))), aux=aux)
        self.values = values
        self.agg_eval = agg_template

    def __str__(self):
        return self.agg_eval.format(*(str(value) for value in self.values))

    def try_eval(self, consts: Env) -> Optional[Any]:
        evaluated = []
        for value in self.values:
            result = value.try_eval(consts)
            if result is None:
                return None
            evaluated.append(result)
        return eval(self.agg_eval.format(*evaluated))


class EqualTest(AggValue):
    def __init__(self, reg: Reg, value: Value):
        super().__init__([Value([reg], '{0}'), value], '{0} == {1}')
        self.equal_reg = reg
        self.equal_value = value


class BasicBlock:
    count = 0

    def __init__(self, codes: List[Instr] = None, cond: Value = None,
                 yes_block: BasicBlock = None,
                 no_block: BasicBlock = None):
        self.codes = codes or []
        if cond is None:
            assert yes_block is None and no_block is None
        else:
            assert yes_block is not None and no_block is not None
        self.cond = cond
        self.yes_block = yes_block
        self.no_block = no_block
        self.block_id = BasicBlock.count
        BasicBlock.count += 1

    @staticmethod
    def build_dep_graph(codes: List[Instr], cond: Value = None) -> Dict[Union[Instr, Value], Set[Instr]]:
        dep_graph: Dict[Union[Instr, Value], Set[Instr]] = {}
        # all instructions that (possibly) processes the last writing to a register,
        # and all instructions that read the register after the last writing
        reg_graph: Dict[Reg, Tuple[List[Instr], List[Instr]]] = {}
        for instr in cast(List[SetValue], codes):
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
                if isinstance(instr, If):
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
            for read_reg in cond.regs:
                if read_reg in reg_graph and reg_graph[read_reg][0] is not None:
                    dep_graph[cond].update(reg_graph[read_reg][0])
        return dep_graph

    @staticmethod
    def scan_codes(codes: List[Instr], agg_choice: Value = None) -> Tuple[List[Instr], bool]:
        choice = False
        agg_choice = agg_choice or Value([])
        dep_graph = BasicBlock.build_dep_graph(codes, agg_choice)
        scanned: List[Optional[Instr]] = [None] * len(codes)
        choice_instr = {instr: instr in dep_graph[agg_choice] for instr in codes}
        for i in (j - 1 for j in range(len(codes), 0, -1)):
            instr = codes[i]
            if isinstance(instr, Command) and instr.opt_target:
                choice = True
                agg_choice = Value(list(set(agg_choice.regs + instr.read_regs)))
            if isinstance(instr, If):
                scanned_yes, choice_yes = BasicBlock.scan_codes(instr.yes, agg_choice)
                scanned_no, choice_no = BasicBlock.scan_codes(instr.no, agg_choice)
                if choice_yes or choice_no:
                    choice = True
                    agg_choice = Value(list(set(agg_choice.regs + instr.read_regs)))
                if choice_yes or choice_no or choice_instr[instr]:
                    for dep_instr in dep_graph[instr]:
                        choice_instr[dep_instr] = True
                    scanned[i] = Choice(instr.cond, scanned_yes, scanned_no)
                else:
                    scanned[i] = instr
            else:
                if choice_instr[instr]:
                    for dep_instr in dep_graph[instr]:
                        choice_instr[dep_instr] = True
                scanned[i] = instr
        assert all(instr is not None for instr in scanned)
        return cast(List[Instr], scanned), choice

    @staticmethod
    def from_codes(codes: List[Instr]) -> BasicBlock:
        scanned, _ = BasicBlock.scan_codes(codes)
        return BasicBlock(scanned)

    def eval_reduce(self, consts: Env = None) -> BasicBlock:
        consts = cast(Env, consts or {})
        affected_consts = dict(consts)
        for i, instr in enumerate(self.codes):
            if isinstance(instr, If):
                prev_codes = self.codes[:i]
                after_codes = self.codes[i + 1:]
                choice_cond = instr.cond.try_eval(affected_consts)
                if choice_cond is not None:
                    if choice_cond != 0:
                        codes = prev_codes + instr.yes + after_codes
                    else:
                        codes = prev_codes + instr.no + after_codes
                    return BasicBlock(codes, self.cond, self.yes_block, self.no_block).eval_reduce(consts)
                elif isinstance(instr, Choice):
                    # beg for this not too heavy
                    codes = prev_codes
                    cond = instr.cond
                    yes_block = BasicBlock(instr.yes + after_codes, self.cond, self.yes_block,
                                           self.no_block)
                    no_block = BasicBlock(instr.no + after_codes, self.cond, self.yes_block,
                                          self.no_block)
                    return BasicBlock(codes, cond, yes_block, no_block).eval_reduce(consts)
            affected_consts = instr.affect(affected_consts)
        if self.cond is None:
            return self
        assert self.yes_block is not None and self.no_block is not None
        cond_value = self.cond.try_eval(affected_consts)
        if cond_value is not None:
            if bool(cond_value):
                selected_block = self.no_block.eval_reduce(affected_consts)
            else:
                selected_block = self.yes_block.eval_reduce(affected_consts)
            return BasicBlock(self.codes + selected_block.codes, selected_block.cond,
                              selected_block.yes_block,
                              selected_block.no_block)
        else:
            yes_consts = affected_consts
            if isinstance(self.cond, EqualTest):
                equal_value = self.cond.equal_value.try_eval(affected_consts)
                if equal_value is not None:
                    yes_consts = dict(affected_consts)
                    yes_consts[self.cond.equal_reg] = equal_value
            yes_block = self.yes_block.eval_reduce(yes_consts)
            no_block = self.no_block.eval_reduce(affected_consts)
            if yes_block is self.yes_block and no_block is self.no_block:
                return self
            return BasicBlock(self.codes, self.cond, yes_block, no_block)

    def __str__(self):
        label_line = f'L{self.block_id}:\n'
        code_lines = [str(instr) for instr in self.codes]
        if self.cond is not None:
            code_lines.append(f'Goto If {self.cond} L{self.yes_block.block_id} Else L{self.no_block.block_id}')
        if not code_lines:
            code_lines = ['Nop']
        return label_line + '\n'.join(code_lines)

    def recurse(self) -> Generator[BasicBlock, None, None]:
        yield self
        if self.cond is not None:
            assert self.yes_block is not None and self.no_block is not None
            yield from self.yes_block.recurse()
            yield from self.no_block.recurse()

    class IfDep(Exception):
        def __init__(self, i, instr):
            super().__init__()
            self.i = i
            self.instr = instr

    def build_fixed(self) -> List[bool]:
        fixed = [False] * len(self.codes)
        assert self.cond is not None
        read_regs = set(self.cond.regs)
        write_regs: Set[Reg] = set()
        command_write: Set[Reg] = set()
        for i in (j - 1 for j in range(len(self.codes), 0, -1)):
            instr = self.codes[i]
            instr_read = set(instr.read_regs)
            instr_write = set(instr.write_regs)
            if instr_write & read_regs or instr_read & write_regs or instr_write & write_regs:
                if not instr_read & command_write and isinstance(instr, If):
                    raise BasicBlock.IfDep(i, instr)
                fixed[i] = True
                read_regs.update(instr.read_regs)
                write_regs.update(instr.write_regs)
                # if isinstance(instr, SetValue):
                #     read_regs.discard(instr.reg)
                if isinstance(instr, Command):
                    command_write.update(instr.write_regs)
            # else:
            #     if isinstance(instr, SetValue):
            #         write_regs.discard(instr.reg)
        return fixed

    def relocate_cond(self) -> BasicBlock:
        if self.cond is None:
            return self
        assert self.yes_block is not None and self.no_block is not None

        try:
            fixed = self.build_fixed()
        except BasicBlock.IfDep as if_dep:
            i, instr = if_dep.i, if_dep.instr
            # condition is blocked by (at least) one If
            # expand this If may remove the blocker to some extent
            # note: there's a little duplicated work here
            codes = self.codes[:i]
            cond = instr.cond
            rest_codes = self.codes[i + 1:]
            yes_block = BasicBlock(instr.yes + rest_codes, self.cond, self.yes_block, self.no_block)
            no_block = BasicBlock(rest_codes, self.cond, self.yes_block, self.no_block)
            return BasicBlock(codes, cond, yes_block, no_block).relocate_cond()

        # except BasicBlock.IfDep:
        #     # after preprocess in scan_codes, there should be no dependent If exists
        #     raise

        fixed_codes = [instr for i, instr in enumerate(self.codes) if fixed[i]]
        shifted_codes = [instr for i, instr in enumerate(self.codes) if not fixed[i]]
        if shifted_codes:
            yes_block = BasicBlock(shifted_codes + self.yes_block.codes, self.yes_block.cond,
                                   self.yes_block.yes_block,
                                   self.yes_block.no_block).relocate_cond()
            no_block = BasicBlock(shifted_codes + self.no_block.codes, self.no_block.cond,
                                  self.no_block.yes_block,
                                  self.no_block.no_block).relocate_cond()
        else:
            yes_block = self.yes_block.relocate_cond()
            no_block = self.no_block.relocate_cond()
        if yes_block is self.yes_block and no_block is self.no_block:
            return self
        return BasicBlock(fixed_codes, self.cond, yes_block, no_block)

    def optimize(self) -> BasicBlock:
        block = self
        while True:
            opt_block = block.eval_reduce().relocate_cond()
            if opt_block is block:
                return block
            block = opt_block
