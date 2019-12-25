from typing import List, cast, Dict, Tuple, Optional, Generator


class Instr:
    def __init__(self, read_regs: List[int], write_regs: List[int]):
        self.read_regs = read_regs
        self.write_regs = write_regs

    def affect(self, env: Dict[int, int]) -> Dict[int, int]:
        raise NotImplementedError()


class SetValue(Instr):
    def __init__(self, reg: int, value: 'Value'):
        super(SetValue, self).__init__(value.regs, [reg])
        self.reg = reg
        self.value = value

    def __str__(self):
        return f'${self.reg} = {self.value}'

    def affect(self, env: Dict[int, int]) -> Dict[int, int]:
        reg_value = self.value.try_eval(env)
        if reg_value is not None:
            env[self.reg] = reg_value
        return env


class Command(SetValue):
    def __init__(self, provider: int, name: str, args: List['Value'], opt_target: bool = False):
        super(Command, self).__init__(provider, AggValue(args, '<should not evaluate>'))
        self.provider = provider
        self.name = name
        self.args = args
        self.opt_target = opt_target

    def __str__(self):
        args_str = ', '.join(str(arg) for arg in self.args)
        return f'${self.provider}->{self.name}({args_str})'

    def affect(self, env: Dict[int, int]) -> Dict[int, int]:
        return env


class If(Instr):
    def __init__(self, cond: 'Value', yes: List[Instr], no: List[Instr] = None):
        self.cond = cond
        self.yes = yes
        self.no = no or []

        read_regs = set(cond.regs)
        write_regs = set()
        for instr in self.yes + self.no:
            read_regs.update(instr.read_regs)
            write_regs.update(instr.write_regs)
        super(If, self).__init__(list(read_regs), list(write_regs))

    def affect(self, env: Dict[int, int]) -> Dict[int, int]:
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
    def __init__(self, cond: 'Value', yes: List[Instr], no: List[Instr]):
        super().__init__(cond, yes, no)

    def __str__(self):
        yes_str = '\n'.join(str(instr) for instr in self.yes)
        no_str = '\n'.join(str(instr) for instr in self.no)
        if yes_str:
            yes_str = '\n' + yes_str.replace('\n', '\n  ') + '\n'
        if no_str:
            no_str = '\n' + no_str.replace('\n', '\n  ') + '\n'
        return f'Choice {self.cond} {{{yes_str}}} Else {{{no_str}}}'


class Value:
    def __init__(self, regs: List[int], eval_template: str = '<should not evaluate>'):
        self.regs = regs
        self.eval_template = eval_template

    def __str__(self):
        return self.eval_template.format(*(f'${reg}' for reg in self.regs))

    def try_eval(self, consts: Dict[int, int]) -> Optional[int]:
        reg_values = []
        for reg in self.regs:
            if reg not in consts:
                return None
            reg_values.append(consts[reg])
        return eval(self.eval_template.format(*reg_values))


class AggValue(Value):
    def __init__(self, values: List[Value], agg_template: str):
        super().__init__(list(set(sum((value.regs for value in values), []))))
        self.values = values
        self.agg_eval = agg_template

    def __str__(self):
        return self.agg_eval.format(*(str(value) for value in self.values))

    def try_eval(self, consts: Dict[int, int]) -> Optional[int]:
        evaluated = []
        for value in self.values:
            result = value.try_eval(consts)
            if result is None:
                return None
            evaluated.append(result)
        return eval(self.agg_eval.format(*evaluated))


class EqualTest(AggValue):
    def __init__(self, reg: int, value: Value):
        super().__init__([Value([reg], '{0}'), value], '{0} == {1}')
        self.equal_reg = reg
        self.equal_value = value


class BasicBlock:
    count = 0

    def __init__(self, codes: List[Instr] = None, cond: Value = None,
                 yes_block: 'BasicBlock' = None,
                 no_block: 'BasicBlock' = None):
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
    def scan_codes(codes: List[Instr]) -> Tuple[List[Instr], bool]:
        choice = False
        scanned = []
        for instr in codes:
            if isinstance(instr, Command) and instr.opt_target:
                choice = True
            if isinstance(instr, If):
                scanned_yes, choice_yes = BasicBlock.scan_codes(instr.yes)
                scanned_no, choice_no = BasicBlock.scan_codes(instr.no)
                if choice_yes or choice_no:
                    choice = True
                    scanned.append(Choice(instr.cond, scanned_yes, scanned_no))
                else:
                    scanned.append(instr)
            else:
                scanned.append(instr)
        return scanned, choice

    @staticmethod
    def from_codes(codes: List[Instr]) -> 'BasicBlock':
        scanned, _ = BasicBlock.scan_codes(codes)
        return BasicBlock.recursive_build(scanned)

    @staticmethod
    def recursive_build(codes: List[Instr]) -> 'BasicBlock':
        # https://stackoverflow.com/a/8534381
        first_if_index = next((i for i, instr in enumerate(codes) if isinstance(instr, Choice)), len(codes))
        block_codes = codes[:first_if_index]
        if first_if_index == len(codes):
            return BasicBlock(block_codes)
        else:
            if_instr = cast(If, codes[first_if_index])
            cond = if_instr.cond
            rest_codes = codes[first_if_index + 1:]
            yes_codes = if_instr.yes + rest_codes
            no_codes = if_instr.no + rest_codes
            return BasicBlock(block_codes, cond, BasicBlock.recursive_build(yes_codes),
                              BasicBlock.recursive_build(no_codes))

    def eval_reduce(self, consts: Dict[int, int] = None) -> 'BasicBlock':
        consts = cast(Dict[int, int], consts or {})
        if self.cond is None:
            return self
        for instr in self.codes:
            consts = instr.affect(consts)
        cond_value = self.cond.try_eval(consts)
        if cond_value is not None:
            if cond_value == 0:
                selected_block = self.no_block.eval_reduce(consts)
            else:
                selected_block = self.yes_block.eval_reduce(consts)
            return BasicBlock(self.codes + selected_block.codes, selected_block.cond, selected_block.yes_block,
                              selected_block.no_block)
        else:
            yes_consts = dict(consts)
            if isinstance(self.cond, EqualTest):
                equal_value = self.cond.equal_value.try_eval(consts)
                yes_consts[self.cond.equal_reg] = equal_value
            yes_block = self.yes_block.eval_reduce(yes_consts)
            no_block = self.no_block.eval_reduce(consts)
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

    def recursive(self) -> Generator['BasicBlock', None, None]:
        yield self
        if self.cond is not None:
            yield from self.yes_block.recursive()
            yield from self.no_block.recursive()

    class IfDep(Exception):
        def __init__(self, i, instr):
            super().__init__()
            self.i = i
            self.instr = instr

    def build_fixed(self) -> List[bool]:
        fixed = [False] * len(self.codes)
        if self.cond is None:
            return fixed
        read_regs = set(self.cond.regs)
        write_regs = set()
        for i_1 in range(len(self.codes), 0, -1):
            i = i_1 - 1
            instr = self.codes[i]
            instr_read = set(instr.read_regs)
            instr_write = set(instr.write_regs)
            if instr_write & read_regs or instr_read & write_regs or instr_write & write_regs:
                if isinstance(instr, If):
                    raise BasicBlock.IfDep(i, instr)
                fixed[i] = True
                read_regs.update(instr.read_regs)
                write_regs.update(instr.write_regs)
                if isinstance(instr, SetValue):
                    for write_reg in instr.write_regs:
                        read_regs.discard(write_reg)
        return fixed

    def relocate_cond(self) -> 'BasicBlock':
        if self.cond is None:
            return self

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

        fixed_codes = [instr for i, instr in enumerate(self.codes) if fixed[i]]
        shifted_codes = [instr for i, instr in enumerate(self.codes) if not fixed[i]]
        if shifted_codes:
            yes_block = BasicBlock(shifted_codes + self.yes_block.codes, self.yes_block.cond,
                                   self.yes_block.yes_block,
                                   self.yes_block.no_block).relocate_cond()
            no_block = BasicBlock(shifted_codes + self.no_block.codes, self.no_block.cond, self.no_block.yes_block,
                                  self.no_block.no_block).relocate_cond()
        else:
            yes_block = self.yes_block.relocate_cond()
            no_block = self.no_block.relocate_cond()
        if yes_block is self.yes_block and no_block is self.no_block:
            return self
        return BasicBlock(fixed_codes, self.cond, yes_block, no_block)
