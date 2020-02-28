# interface definition
# all implementation for compilation lives in weaver.compile
from weaver.util import indent_join
from weaver.compile import (
    compile1_layout,
    compile1_header_action,
    compile2_layout,
    compile4_const,
    compile4_op2,
    compile4_op1,
    compile4_var,
    compile4_payload,
    compile5_assign,
    compile5_action,
    eval1_const,
)


class HeaderActionOpMixin:
    def __add__(self, other):
        return HeaderAction([self, other])


class LayoutMeta(type, HeaderActionOpMixin):
    def __init__(self, *args):
        super().__init__(*args)
        self.name_map = {
            name: value
            for name, value in self.__dict__.items()
            if not name.startswith("_")
        }

    def __str__(self):
        return f"parse({self.__name__})"

    def compile1(self, context):
        return compile1_layout(self, context)

    def compile2(self, context):
        return compile2_layout(self, context)


class layout(metaclass=LayoutMeta):
    pass


class NameMapMixin:
    def __init__(self):
        self.init = True

    def __setattr__(self, name, value):
        if not hasattr(self, "init") or hasattr(self, name):
            super().__setattr__(name, value)
        else:
            self.name_map[name] = value

    def __getattr__(self, name):
        try:
            return getattr(super(), name)
        except AttributeError:
            if name == "init":
                raise
            return self.name_map[name]


class HeaderAction(NameMapMixin):
    def __init__(self, actions):
        self.actions = actions
        self.name_map = {}
        for action in actions:
            self.name_map = {**self.name_map, **action.name_map}
        super().__init__()

    def __add__(self, other):
        return HeaderAction([*self.actions, other])

    def compile1(self, context):
        return compile1_header_action(self, context)

    def __str__(self):
        return indent_join(str(stat) for stat in self.actions)


class If:
    def __init__(self, pred):
        self.pred = pred

    def __rshift__(self, action):
        return IfElse(self.pred, action, Action([]))


class Action:
    def __init__(self, stats):
        self.stats = stats

    def __add__(self, other):
        return Action([*self.stats, other])

    def __str__(self):
        return indent_join(str(stat) for stat in self.stats)

    def compile5(self, context):
        return compile5_action(self, context)


class IfElse(NameMapMixin):
    def __init__(self, pred, yes_action, no_action):
        self.pred = pred
        self.yes_action = yes_action
        self.no_action = no_action
        if hasattr(yes_action, "name_map"):
            self.name_map = yes_action.name_map
        super().__init__()

    def __rshift__(self, else_object):
        return ExpectNoAction(self)

    def __add__(self, other):
        if isinstance(other, HeaderActionOpMixin) or isinstance(other, HeaderAction):
            return HeaderAction([self, other])
        else:
            return Action([self, other])

    def compile1(self):
        pass

    def __str__(self):
        return f"If {self.pred} Then {self.yes_action} Else {self.no_action}"


class ExpectNoAction:
    def __init__(self, ifelse):
        self.ifelse = ifelse

    def __rshift__(self, action):
        return IfElse(self.ifelse.pred, self.ifelse.yes_action, self.ifelse.no_action)


class AnyUntil(HeaderActionOpMixin, NameMapMixin):
    def __init__(self, layouts, pred):
        self.layouts = layouts
        self.pred = pred
        self.name_map = {}
        for layout in layouts:
            self.name_map = {**self.name_map, **layout.name_map}
        super().__init__()

    def compile1(self):
        pass


class perm_fallback(layout):
    pass


class Connectionless:
    def __init__(self):
        self.header = (
            self.selector
        ) = self.temp = self.preprocess = self.seq = self.psm = None
        self.perm = perm_fallback
        self.payload = PayloadExpr()
        self.payload_len = self.payload.length


class NumberOpMixin:
    def __add__(self, other):
        return AddOp(self, Const.wrap_int(other))

    def __lshift__(self, other):
        return LeftShiftOp(self, Const.wrap_int(other))

    def __sub__(self, other):
        return SubOp(self, Const.wrap_int(other))


class Bit(NumberOpMixin):
    def __init__(self, length, init=None):
        self.length = length
        self.init = init

    def __str__(self):
        if self.length is not None:
            return f"$_u{self.length}"
        else:
            return "$_s"

    def compile4(self, context):
        return compile4_var(self, context)


class SliceOpMixin:
    def __getitem__(self, key):
        if isinstance(key, slice):
            if key.start is not None:
                if key.stop is not None:
                    return SliceAfterOp(
                        SliceBeforeOp(self, Const.wrap_int(key.stop)),
                        Const.wrap_int(key.start),
                    )
                else:
                    return SliceAfterOp(self, Const.wrap_int(key.start))
            elif key.stop is not None:
                return SliceBeforeOp(self, Const.wrap_int(key.stop))
            else:
                return self
        else:
            return SliceGetOp(self, Const.wrap_int(key))

    @property
    def length(self):
        return SliceLengthOp(self)


class ActionOpMixin:
    def __add__(self, other):
        return Action([self, other])


class Assign(ActionOpMixin):
    def __init__(self, var, expr):
        self.var = var
        self.expr = Const.wrap_int(expr)

    def __str__(self):
        return f"Assign {self.var} <- {self.expr}"

    def compile5(self, context):
        return compile5_assign(self, context)


# Only unsigned integer constants are initialized as Const
# empty slice is the only slice constant that could be created currently
class Const:
    def __init__(self, value):
        self.value = value

    @staticmethod
    def wrap_int(value):
        if isinstance(value, int):
            return Const(value)
        else:
            return value

    def __str__(self):
        return f"Const({self.value})"

    def compile4(self, context):
        return compile4_const(self)

    def eval1(self, context):
        return eval1_const(self)


class Sequence:
    def __init__(self, meta, data, zero_based=True, data_len=Const(0)):
        self.offset = meta
        self.data = data
        self.zero_based = zero_based
        self.takeup = data_len


# Op
class AddOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) + ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("add", self.expr1, self.expr2, context)


class SubOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) - ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("sub", self.expr1, self.expr2, context)


class LeftShiftOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) << ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("left_shift", self.expr1, self.expr2, context)


class SliceBeforeOp(SliceOpMixin):
    def __init__(self, slice, index):
        self.slice = slice
        self.index = index

    def __str__(self):
        return f"({self.slice})[:{self.index}]"

    def compile4(self, context):
        return compile4_op2("slice_before", self.slice, self.index, context)


class SliceAfterOp(SliceOpMixin):
    def __init__(self, slice, index):
        self.slice = slice
        self.index = index

    def __str__(self):
        return f"({self.slice})[{self.index}:]"

    def compile4(self, context):
        return compile4_op2("slice_after", self.slice, self.index, context)


class SliceGetOp(NumberOpMixin):
    def __init__(self, slice, index):
        self.slice = slice
        self.index = index

    def __str__(self):
        return f"({self.slice})[{self.index}]"

    def compile4(self, context):
        return compile4_op2("slice_get", self.slice, self.index, context)


class SliceLengthOp(NumberOpMixin):
    def __init__(self, slice):
        self.slice = slice

    def __str__(self):
        return f"({self.slice}).length"

    def compile4(self, context):
        return compile4_op1("slice_length", self.slice, context)


class PayloadExpr(SliceOpMixin):
    def __str__(self):
        return "payload"

    def compile4(self, context):
        return compile4_payload()
