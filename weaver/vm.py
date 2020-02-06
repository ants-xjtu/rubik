from __future__ import annotations
from typing import Dict, NewType


class NotConstant(Exception):
    pass


class ValueTy:
    pass


class Unsigned(ValueTy):
    def __init__(self, byte_length: int):
        super().__init__()
        self.byte_length = byte_length

    def const(self, value: int):
        assert 0 <= value < (1 << (self.byte_length * 8))
        return ConstUnsigned(self, value)


class Bool(ValueTy):
    def const(self, value: bool):
        return ConstBool(value)


class Expr:
    def __init__(self, ty: ValueTy):
        self.ty = ty

    def evaluate(self, env: EvalEnv) -> ConstValue:
        raise NotConstant()

    def generate(self, env: GenEnv) -> str:
        raise NotImplementedError()


class ConstValue(Expr):
    def __init__(self, ty: ValueTy):
        self.ty = ty

    def evaluate(self, env: EvalEnv) -> ConstValue:
        return self


class ConstUnsigned(ConstValue):
    def __init__(self, ty: ValueTy, value: int):
        assert isinstance(ty, Unsigned)
        super().__init__(ty)
        self.value = value

    def generate(self, env: GenEnv) -> str:
        return str(self.value)


u8_zero = Unsigned(1).const(0)
u16_zero = Unsigned(2).const(0)
u32_zero = Unsigned(3).const(0)
u64_zero = Unsigned(4).const(0)
u8_one = Unsigned(1).const(1)
u16_one = Unsigned(2).const(1)
u32_one = Unsigned(3).const(1)
u64_one = Unsigned(4).const(1)


class ConstBool(ConstValue):
    def __init__(self, value: bool):
        super().__init__(Bool())
        self.value = value

    def generate(self, env: GenEnv) -> str:
        if self.value:
            return u8_one.generate(env)
        else:
            return u8_zero.generate(env)


true = Bool().const(True)
false = Bool().const(False)


Reg = NewType('Reg', int)


class EvalEnv:
    def __init__(self):
        self.table: Dict[Reg, ConstValue] = {}

    def set_reg(self, reg: Reg, value: ConstValue):
        self.table[reg] = value

    def get_reg(self, reg: Reg) -> ConstValue:
        if reg not in self.table:
            raise NotConstant()
        return self.table[reg]


class GenEnv:
    def __init__(self, table: Dict[Reg, str]):
        self.table = table

    def get_reg(self, reg: Reg) -> str:
        return self.table[reg]


class LoadReg(Expr):
    def __init__(self, ty: ValueTy, reg: Reg):
        super().__init__(ty)
        self.reg = reg

    def evaluate(self, env: EvalEnv) -> ConstValue:
        return env.get_reg(self.reg)

    def generate(self, env: GenEnv) -> str:
        return env.get_reg(self.reg)


class UnsignedAddExpr(Expr):
    def __init__(self, expr1: Expr, expr2: Expr):
        assert isinstance(expr1.ty, Unsigned)
        assert isinstance(expr2.ty, Unsigned)
        assert expr1.ty.byte_length == expr2.ty.byte_length
        super().__init__(expr1.ty)
        self.expr1 = expr1
        self.expr2 = expr2
        self.max = 1 << (expr1.ty.byte_length * 8) - 1

    def evaluate(self, env: EvalEnv) -> ConstValue:
        return ConstUnsigned(
            self.ty,
            min(self.expr1.evaluate(env) + self.expr2.evaluate(env), self.max - 1)
        )

    def generate(self, env: GenEnv) -> str:
        core_text = f'({self.expr1.generate(env)} + {self.expr2.generate(env)})'
        return (
            f'({core_text} < {self.expr1.generate(env)} ||'
            f' {core_text} < {self.expr2.generate(env)} ?'
            f' {self.max} : {core_text})'
        )


class UnsignedEqualExpr(Expr):
    def __init__(self, expr1: Expr, expr2: Expr):
        assert isinstance(expr1.ty, Unsigned)
        assert isinstance(expr2.ty, Unsigned)
        assert expr1.ty.byte_length == expr2.ty.byte_length
        super().__init__(Bool())
        self.expr1 = expr1
        self.expr2 = expr2

    def evaluate(self, env: EvalEnv) -> ConstValue:
        expr1_val = self.expr1.evaluate(env)
        expr2_val = self.expr2.evaluate(env)
        assert isinstance(expr1_val, ConstUnsigned)
        assert isinstance(expr2_val, ConstUnsigned)
        return ConstBool(expr1_val.value == expr2_val.value)

    def generate(self, env: GenEnv) -> str:
        return f'({self.expr1.generate(env)} == {self.expr2.generate(env)})'


class UnsignedRegAssertExpr(UnsignedEqualExpr):
    def __init__(self, ty: ConstUnsigned, reg: Reg, expr: Expr):
        super().__init__(LoadReg(ty, reg), expr)
        self.assert_reg = reg
        self.assert_expr = expr


class Fork:
    def __init__(self, expr: Expr):
        assert isinstance(expr.ty, Bool)
        self.expr = expr

    def asserted(self, env: EvalEnv):
        pass


class UnsignedRegAssertFork(Fork):
    def __init__(self, expr: UnsignedRegAssertExpr):
        super().__init__(expr)

    def asserted(self, env: EvalEnv):
        try:
            env.set_reg(
                self.expr.assert_reg,
                self.expr.assert_expr.evaluate(env)
            )
        except NotConstant:
            pass


class RegStore:
    def __init__(self, table: Dict[Reg, ValueTy]):
        self.table = table

    def get_reg(self, reg: Reg) -> RegHelper:
        return RegHelper(self.table[reg], reg)


class RegHelper:
    def __init__(self, ty: ValueTy, reg: Reg):
        self.ty = ty
        self.reg = reg

    def load(self) -> LoadReg:
        return LoadReg(self.ty, self.reg)

    def equals_to(self, expr: Expr) -> UnsignedRegAssertExpr:
        assert isinstance(self.ty, Unsigned)
        return UnsignedRegAssertExpr(self.ty, self.reg, expr)

    def is_zero(self) -> UnsignedRegAssertExpr:
        return self.equals_to(ConstUnsigned(self.ty, 0))

    def is_one(self) -> UnsignedRegAssertExpr:
        return self.equals_to(ConstUnsigned(self.ty, 1))
