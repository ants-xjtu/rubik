from typing import List, cast, Dict


class Instr:
    pass


class SetValue(Instr):
    def __init__(self, reg: int, value: 'Value'):
        super(SetValue, self).__init__()
        self.reg = reg
        self.value = value

    def __str__(self):
        return f'${self.reg} = {self.value}'


class If(Instr):
    def __init__(self, cond: 'Value', yes: List[Instr], no: List[Instr] = None):
        super(If, self).__init__()
        self.cond = cond
        self.yes = yes
        self.no = no or []


class Value:
    def __init__(self, regs: List[int], eval_template: str):
        self.regs = regs
        self.eval_template = eval_template

    def __str__(self):
        return self.eval_template.format(*(f'${reg}' for reg in self.regs))


class EqualTest(Value):
    def __init__(self, reg: int, value: Value):
        regs = [*value.regs, reg]
        super(EqualTest, self).__init__(regs, f'{{{len(regs) - 1}}} == {value.eval_template}')
        self.reg = reg
        self.value = value


class BasicBlock:
    count = 0

    def __init__(self, codes: List[Instr] = None, cond: Value = None, yes_block: 'BasicBlock' = None,
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

    @classmethod
    def from_codes(cls, codes: List[Instr]) -> 'BasicBlock':
        # https://stackoverflow.com/a/8534381
        first_if_index = next((i for i, instr in enumerate(codes) if isinstance(instr, If)), len(codes))
        block_codes = codes[:first_if_index]
        if first_if_index == len(codes):
            return cls(block_codes)
        else:
            if_instr = cast(If, codes[first_if_index])
            cond = if_instr.cond
            rest_codes = codes[first_if_index + 1:]
            yes_codes = if_instr.yes + rest_codes
            no_codes = if_instr.no + rest_codes
            return cls(block_codes, cond, cls.from_codes(yes_codes), cls.from_codes(no_codes))

    def eval_reduce(self, consts: Dict[int, int] = None) -> 'BasicBlock':
        consts = cast(Dict[int, int], consts or {})
        if self.cond is None:
            return self
        for instr in self.codes:
            if isinstance(instr, SetValue):
                if all(reg in consts for reg in instr.value.regs):
                    reg_values = [consts[reg] for reg in instr.value.regs]
                    consts[instr.reg] = eval(instr.value.eval_template.format(*reg_values))
        if all(reg in consts for reg in self.cond.regs):
            reg_values = [consts[reg] for reg in self.cond.regs]
            cond_value = cast(int, eval(self.cond.eval_template.format(*reg_values)))
            if cond_value == 0:
                selected_block = self.no_block.eval_reduce(consts)
            else:
                selected_block = self.yes_block.eval_reduce(consts)
            return BasicBlock(self.codes + selected_block.codes, selected_block.cond, selected_block.yes_block,
                              selected_block.no_block)
        elif isinstance(self.cond, EqualTest) and all(reg in consts for reg in self.cond.value.regs):
            reg_values = [consts[reg] for reg in self.cond.value.regs]
            equal_value = cast(int, eval(self.cond.value.eval_template.format(*reg_values)))
            yes_consts = {**consts, self.cond.reg: equal_value}
            return BasicBlock(self.codes, self.cond, self.yes_block.eval_reduce(yes_consts),
                              self.no_block.eval_reduce(consts))
        else:
            return self

    def __str__(self):
        label_line = f'L{self.block_id}:\n'
        code_lines = [str(instr) for instr in self.codes]
        if self.cond is not None:
            code_lines.append(f'If {self.cond} Goto L{self.yes_block.block_id} Else Goto L{self.no_block.block_id}')
        if not code_lines:
            code_lines = ['Nop']
        return label_line + '\n'.join(code_lines)

    def recursive(self):
        yield self
        if self.cond is not None:
            yield from self.yes_block.recursive()
            yield from self.no_block.recursive()
