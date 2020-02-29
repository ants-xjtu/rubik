# interface definition
# all implementation for compilation lives in weaver.compile
# NOTICE: only import when duck type is needed, if not, use functions in weaver.compile directly
# as interface
from weaver.util import indent_join
from weaver.compile import (
    StackContext,
    compile1_layout,
    compile1_header_action,
    compile1_any_until,
    compile1_if,
    compile3a_prototype,
    compile4_const,
    compile4_op2,
    compile4_op1,
    compile4_var,
    compile4_payload,
    compile4_total,
    compile4_header_contain,
    compile4_foreign_var,
    compile4_empty,
    compile5_assign,
    compile5_action,
    compile5_if,
    eval1_const,
)


class HeaderActionOpMixin:
    def __add__(self, other):
        return HeaderAction([self, other])


class LayoutMeta(type, HeaderActionOpMixin):
    def __init__(self, *args):
        super().__init__(*args)
        self.field_list = [
            (name, value)
            for name, value in self.__dict__.items()
            if not name.startswith("_")
        ]
        self.name_map = {name: value for name, value in self.field_list}

    def __str__(self):
        return f"parse({self.__name__})"

    def compile1(self, context):
        return compile1_layout(self, context)


class layout(metaclass=LayoutMeta):
    pass


class NameMapMixin:
    def __init__(self):
        self.init = True

    def __setattr__(self, name, value):
        try:
            if hasattr(self, "init"):
                _ = super().__getattribute__(name)
            super().__setattr__(name, value)
        except AttributeError:
            self.name_map[name] = self.handle_set(value)

    def handle_set(self, value):
        return value

    def __getattr__(self, name):
        if name == "init":
            raise AttributeError()
        return self.handle_get(self.name_map[name])

    def handle_get(self, value):
        return value


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


class Else:
    pass


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

    def compile1(self, context):
        return compile1_if(self, context)

    def __str__(self):
        return f"If {self.pred} Then {self.yes_action} Else {self.no_action}"

    def compile5(self, context):
        return compile5_if(self, context)


class ExpectNoAction:
    def __init__(self, ifelse):
        self.ifelse = ifelse

    def __rshift__(self, action):
        return IfElse(self.ifelse.pred, self.ifelse.yes_action, action)


class AnyUntil(HeaderActionOpMixin, NameMapMixin):
    def __init__(self, layouts, pred):
        self.layouts = layouts
        self.pred = pred
        self.name_map = {}
        for layout in layouts:
            self.name_map = {**self.name_map, **layout.name_map}
        super().__init__()

    def compile1(self, context):
        return compile1_any_until(self, context)


class perm_fallback(layout):
    pass


class Prototype:
    def __init__(self):
        self.header = (
            self.selector
        ) = self.temp = self.preprocess = self.seq = self.psm = None
        self.perm = perm_fallback

        self.payload = PayloadExpr()
        self.payload_len = self.payload.length
        self.total_len = TotalExpr().length
        self.cursor = self.total_len - self.payload_len

        self.current_state = Bit(8, init=0)
        self.trans = Bit(16)
        self.to_active = Bit(8)
        self.to_passive = NotOp(self.to_active)

    def header_contain(self, layout):
        return HeaderContainOp(layout)


Connectionless = ConnectionOriented = Prototype


class UniversalNumberOpMixin:
    def __add__(self, other):
        return AddOp(self, Const.wrap_int(other))

    def __lshift__(self, other):
        return LeftShiftOp(self, Const.wrap_int(other))

    def __sub__(self, other):
        return SubOp(self, Const.wrap_int(other))

    def __lt__(self, other):
        return LessThanOp(self, Const.wrap_int(other))

    def __eq__(self, other):
        return EqualOp(self, Const.wrap_int(other))

    def __ne__(self, other):
        return NotOp(EqualOp(self, Const.wrap_int(other)))


# used by compounded expressions
class NumberOpMixin(UniversalNumberOpMixin):
    def __and__(self, other):
        return LogicalAndOp(self, other)

    def __or__(self, other):
        return LogicalOrOp(self, other)


class Bit(UniversalNumberOpMixin):
    def __init__(self, length=None, init=None, const=None):
        self.length = length
        self.init = Const.wrap_int(init)
        self.const = const

        self.var_id = lambda: None

    def __str__(self):
        if isinstance(self.length, int):
            return f"$<_u{self.length}>"
        else:
            return "$<_s>"

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


class NoData:
    def __str__(self):
        return "EmptySlice"

    def compile4(self, context):
        return compile4_empty()


class Sequence:
    def __init__(self, meta, data, zero_based=True, data_len=Const(0), window=None):
        self.offset = meta
        self.data = data
        self.zero_based = zero_based
        self.takeup = data_len
        if window is None:
            self.window_left = self.window_right = Const(0)
        else:
            self.window_left, self.window_right = window


class Stack(NameMapMixin):
    def __init__(self, name_map=None, next_map=None):
        self.name_map = name_map or {}
        self.next_map = next_map or {}
        self.context = StackContext()
        self.layer_count = 0
        super().__init__()

    def handle_set(self, prototype):
        layer = Layer(prototype, self.context, self.layer_count)
        self.layer_count += 1
        self.next_map[layer] = []
        return layer

    def __iadd__(self, dir_pred):
        self.next_map[dir_pred.src].append((dir_pred.pred, dir_pred.dst))
        return self


class Layer:
    def __init__(self, prototype, stack, layer_id):
        self.layer = compile3a_prototype(prototype, stack, layer_id)
        self.header = ForeignNameMap(self.layer.header, self.layer.context)
        if self.layer.temp is not None:
            self.temp = ForeignNameMap(self.layer.temp, self.layer.context)
        if self.layer.perm is not None:
            self.perm = ForeignNameMap(self.layer.perm, self.layer.context)

    def __rshift__(self, dst_layer):
        return Direction(self, dst_layer)


class ForeignNameMap(NameMapMixin):
    def __init__(self, provider, context):
        self.name_map = provider.name_map
        self.context = context
        super().__init__()

    def handle_get(self, var):
        return ForeignVar(self.context.query(var))


class ForeignVar:
    def __init__(self, reg):
        self.reg = reg

    def compile4(self, context):
        return compile4_foreign_var(self.reg, context)


class Direction:
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

    def __add__(self, pred):
        return DirPred(self.src, self.dst, pred.pred, Action([]))


class Predicate:
    def __init__(self, pred):
        self.pred = Const.wrap_int(pred)


class DirPred:
    def __init__(self, src, dst, pred, action):
        self.src = src
        self.dst = dst
        self.pred = pred
        self.action = action

    def __add__(self, stat):
        return DirPred(self.src, self.dst, self.pred, self.action + stat)


class PSMState:
    def __init__(self, start=False, accept=False):
        self.start = start
        self.accept = accept
        self.machine = None
        self.state_id = None

    def __rshift__(self, dst_state):
        return Direction(self, dst_state)

    def compile4(self, context):
        assert self.state_id is not None
        return Const(self.state_id).compile4(context)


def make_psm_state(count, accept=False):
    return tuple(PSMState(accept=accept) for i in range(count))


class PSM(NameMapMixin):
    def __init__(self, *states):
        self.name_map = {}
        self.accept_list = []
        self.trans_list = []
        self.state_map = {}

        self.trans_var = None

        state_count = 1
        for state in states:
            assert state.machine is None
            state.machine = self
            if state.start:
                state.state_id = 0
            else:
                state.state_id = state_count
                state_count += 1
            if state.accept:
                self.accept_list.append(state)
            self.state_map[state.state_id] = []
        super().__init__()

    def handle_set(self, dir_pred):
        trans = PSMTrans(dir_pred.pred, dir_pred.dst.state_id, dir_pred.action)
        self.trans_list.append(trans)
        trans_id = len(self.trans_list)  # count from 1, 0 means not triggered yet
        self.state_map[dir_pred.src.state_id].append(trans_id)
        return trans_id

    def handle_get(self, name):
        assert self.trans_var is not None
        return self.trans_var == self.name_map[name]


class PSMTrans:
    def __init__(self, pred, dst_state, action):
        self.pred = pred
        self.dst_state = dst_state
        self.action = action


# Op
class HeaderContainOp(NumberOpMixin):
    def __init__(self, layout):
        self.layout = layout

    def compile4(self, context):
        return compile4_header_contain(self.layout, context)


class AddOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) + ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("add", self.expr1, self.expr2, context)


class LogicalOrOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) or ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("or", self.expr1, self.expr2, context)


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


class LessThanOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) < ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("less_than", self.expr1, self.expr2, context)


class EqualOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) == ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("equal", self.expr1, self.expr2, context)


class LogicalAndOp(NumberOpMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) and ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("and", self.expr1, self.expr2, context)


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


class NotOp(NumberOpMixin):
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return f"not ({self.expr})"

    def compile4(self, context):
        return compile4_op1("not", self.expr, context)


class PayloadExpr(SliceOpMixin):
    def __str__(self):
        return "payload"

    def compile4(self, context):
        return compile4_payload()


class TotalExpr(SliceOpMixin):
    def __str__(self):
        return "total"

    def compile4(self, context):
        return compile4_total()
