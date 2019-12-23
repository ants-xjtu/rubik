from typing import List, cast, Dict, Tuple, Set, Optional, Union


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


class Value:
    def __init__(self, regs: List[int], eval_template: str):
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


class EqualTest(Value):
    def __init__(self, reg: int, value: Value):
        regs = [*value.regs, reg]
        super(EqualTest, self).__init__(regs, f'{{{len(regs) - 1}}} == {value.eval_template}')
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
    def from_codes(codes: List[Instr]) -> 'BasicBlock':
        # https://stackoverflow.com/a/8534381
        first_if_index = next((i for i, instr in enumerate(codes) if isinstance(instr, If)), len(codes))
        block_codes = codes[:first_if_index]
        if first_if_index == len(codes):
            return BasicBlock(block_codes)
        else:
            if_instr = cast(If, codes[first_if_index])
            cond = if_instr.cond
            rest_codes = codes[first_if_index + 1:]
            yes_codes = if_instr.yes + rest_codes
            no_codes = if_instr.no + rest_codes
            return BasicBlock(block_codes, cond, BasicBlock.from_codes(yes_codes),
                              BasicBlock.from_codes(no_codes))

    @staticmethod
    def build_dep_graph(codes: List[Instr], cond: Value = None) -> Dict[Union[Instr, Value], Set[Instr]]:
        dep_graph: Dict[Union[Instr, Value], Set[Instr]] = {}
        # the instruction that processes the last writing to a register,
        # and all instructions that read the register after the last writing
        reg_graph: Dict[int, Tuple[Optional[Instr], List[Instr]]] = {}
        for instr in cast(List[SetValue], codes):
            dep_graph[instr] = set()
            for write_reg in instr.write_regs:
                # the writing must be after all the readings which expect the old value
                # the writing also must be after the previous writing to prevent to store wrong value eventually
                if write_reg in reg_graph:
                    prev_write, all_read = reg_graph[write_reg]
                    if prev_write is not None:
                        dep_graph[instr].add(prev_write)
                    dep_graph[instr].update(all_read)
            # the reading must be after any writing
            for read_reg in instr.read_regs:
                if read_reg in reg_graph and reg_graph[read_reg][0] is not None:
                    dep_graph[instr].add(reg_graph[read_reg][0])

            # update register graph with current instruction
            for write_reg in instr.write_regs:
                # the writing clears all reading if exist
                reg_graph[write_reg] = instr, []
            # the readings are appended
            for read_reg in instr.read_regs:
                if read_reg not in reg_graph:
                    reg_graph[read_reg] = None, []
                reg_graph[read_reg][1].append(instr)

        if cond is not None:
            dep_graph[cond] = set()
            for read_reg in cond.regs:
                if read_reg in reg_graph and reg_graph[read_reg][0] is not None:
                    dep_graph[cond].add(reg_graph[read_reg][0])
        return dep_graph

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
        elif isinstance(self.cond, EqualTest):
            equal_value = self.cond.equal_value.try_eval(consts)
            yes_consts = {**consts, self.cond.equal_reg: equal_value}
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

    def relocate_cond(self) -> 'BasicBlock':
        ...
