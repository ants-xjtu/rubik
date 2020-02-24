class OpMixin:
    def __add__(self, other):
        return Add(self, other)

    def __sub__(self, other):
        return Sub(self, other)

    def __lshift__(self, other):
        return LeftShift(self, other)

    def __eq__(self, other):
        return Equal(self, other)


class NumberOpMixin(OpMixin):
    def __add__(self, other):
        return LogicalAdd(self, other)

    def __or__(self, other):
        return LogicalOr(self, other)


class VariableOpMixin(OpMixin):
    def __add__(self, other):
        return BitAnd(self, other)


class SliceOpMixin:
    pass


class Add(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = Constant.wrap(expr1)
        self.expr2 = Constant.wrap(expr2)


class Sub(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = Constant.wrap(expr1)
        self.expr2 = Constant.wrap(expr2)


class LeftShift(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = Constant.wrap(expr1)
        self.expr2 = Constant.wrap(expr2)


class BitAnd(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = Constant.wrap(expr1)
        self.expr2 = Constant.wrap(expr2)


class LogicalAdd(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = Constant.wrap(expr1)
        self.expr2 = Constant.wrap(expr2)


class LogicalOr(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = Constant.wrap(expr1)
        self.expr2 = Constant.wrap(expr2)


class Equal(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = Constant.wrap(expr1)
        self.expr2 = Constant.wrap(expr2)


class LogicalNot(NumberOpMixin):
    def __init__(self, expr):
        self.expr = Constant.wrap(expr)


class SliceLength(NumberOpMixin):
    def __init__(self, expr):
        self.expr = Constant.wrap(expr)


class VExpr(NumberOpMixin):
    def __init__(self, var, expr):
        self.var = var
        self.expr = expr


class Constant(VariableOpMixin):
    def __init__(self, value):
        self.value = value

    @staticmethod
    def wrap(expr):
        if isinstance(expr, int):
            return Constant(expr)
        else:
            return expr


class EmptySlice(SliceOpMixin):
    pass


class Payload(SliceOpMixin):
    pass


class Total(SliceOpMixin):
    pass


class StatOpMixin:
    def __add__(self, other):
        return Action([self, other])


class Assign(StatOpMixin):
    def __init__(self, var, expr):
        self.var = var
        self.expr = Constant.wrap(expr)


class When(StatOpMixin):
    def __init__(self, pred, yes_action, no_action):
        self.pred = Constant.wrap(pred)
        self.yes_action = yes_action
        self.no_action = no_action


class Assemble(StatOpMixin):
    pass


class Action:
    def __init__(self, stats):
        self.stats = stats

    def __add__(self, other):
        if isinstance(other, Action):
            return Action(self.stats + other.stats)
        else:
            return Action(self.stats + [other])
