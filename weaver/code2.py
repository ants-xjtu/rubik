from __future__ import annotations
from typing import Set
from weaver.vm import (
    Expr, Reg, EvalEnv, NotConstant, ConstValue, LoadReg
)


class AbstractValue:
    def __init__(self, read_regs: Set[Reg]):
        self.read_regs = read_regs

    def evaluate(self, env: EvalEnv) -> ConstValue:
        raise NotConstant()


class ExprValue(AbstractValue):
    def __init__(self, expr: Expr):
        self.expr = expr
        super().__init__(self.collect_read_regs())

    def collect_read_regs(self) -> Set[Reg]:
        raise NotImplementedError()


class LoadRegValue(ExprValue):
    def __init__(self, expr: LoadReg):
        super().__init__(expr)

    def collect_read_regs(self) -> Set[Reg]:
        return {self.expr.reg}
