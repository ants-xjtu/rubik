from __future__ import annotations
from typing import List, Dict, TYPE_CHECKING, Any
from weaver.code import SetValue, If, Command

if TYPE_CHECKING:
    from weaver.code import Reg, BasicBlock, Instr


class Runtime:
    def __init__(self):
        self.env: Dict[Reg, Any] = {}

    def set_value(self, reg: Reg, value: Any):
        self.env[reg] = value

    def execute_instr(self, instr: Instr):
        if isinstance(instr, SetValue):
            if isinstance(instr, Command):
                args = [arg.try_eval(self.env) for arg in instr.args]
                assert all(arg is not None for arg in args)
                assert isinstance(self.env[instr.provider], CommandExecutor)
                self.env[instr.provider].execute(instr.name, args, self)
            else:
                value = instr.value.try_eval(self.env)
                assert value is not None
                self.set_value(instr.reg, value)
        else:
            assert isinstance(instr, If)
            cond = instr.cond.try_eval(self.env)
            assert cond is not None
            if bool(cond):
                self.execute_codes(instr.yes)
            else:
                self.execute_codes(instr.no)

    def execute_codes(self, codes: List[Instr]):
        for instr in codes:
            self.execute_instr(instr)

    def execute(self, block: BasicBlock):
        self.execute_codes(block.codes)
        if block.cond is not None:
            cond = block.cond.try_eval(self.env)
            assert cond is not None
            if bool(cond):
                self.execute(block.yes_block)
            else:
                self.execute(block.no_block)

    def register(self, reg: Reg, executor: CommandExecutor):
        self.env[reg] = executor


class CommandExecutor:
    def execute(self, command: str, args: List[Any], runtime: Runtime):
        raise NotImplementedError()
