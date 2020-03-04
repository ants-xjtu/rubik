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
    compile2_if,
    compile2_action,
    compile3a_prototype,
    compile4_const,
    compile4_op2,
    compile4_op1,
    compile4_var,
    compile4_payload,
    compile4_total,
    compile4_content,
    compile4_header_contain,
    compile4_foreign_var,
    compile4_empty,
    compile5_assign,
    compile5_action,
    compile5_assemble,
    compile5_if,
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
        self.debug_name = self.__name__

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
        if name == "init" or name == "name_map":
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

    def compile2(self, context):
        return compile2_action(self, context)


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

    def compile2(self, context):
        return compile2_if(self, context)


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


class Prototype:
    def __init__(self):
        self.header = self.selector = self.temp = self.prep = self.seq = self.psm = None
        self.perm = None
        self.event = EventGroup({}, {}, {})

        self.payload = PayloadExpr()
        self.payload_len = self.payload.length
        self.cursor = TotalExpr().length - self.payload_len
        self.sdu = ContentExpr()

        self.current_state = Bit(8, init=0)
        self.to_active = Bit(8)
        self.to_passive = NotOp(self.to_active)

        self.v = VDomain(self)

    def header_contain(self, layout):
        return HeaderContainOp(layout)


Connectionless = ConnectionOriented = Prototype


class VDomain:
    def __init__(self, prototype):
        self.prototype = prototype

    @property
    def header(self):
        return VNameMap(self.prototype.header)

    @property
    def temp(self):
        return VNameMap(self.prototype.temp)


class VNameMap(NameMapMixin):
    def __init__(self, provider):
        self.name_map = provider.name_map
        super().__init__()

    def handle_get(self, var):
        return VirtualExprIndicator(var)


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
        return LogicalAndOp(self, Const.wrap_int(other))

    def __or__(self, other):
        return LogicalOrOp(self, Const.wrap_int(other))


class Bit(UniversalNumberOpMixin):
    def __init__(self, length=None, init=None, const=None):
        self.length = length
        self.init = Const.wrap_int(init)
        self.const = const

        # var_id takes place because Bit objects (or equivalent) have to be keys of
        # weaver.compile.LayerContext.var_map
        # but Bit.__eq__ is overwritten by UniversalNumberOpMixin (but __hash__ is not)
        # so it cannot be used as key
        # var_id could be any object, as long as uniqueness is guaranteed
        self.var_id = object()

        self.virtual = False

    def __str__(self):
        if isinstance(self.length, int):
            return f"$<_u{self.length}>"
        else:
            return "$<_s>"

    def compile4(self, context):
        return compile4_var(self.var_id, context)


class VirtualExprIndicator(UniversalNumberOpMixin):
    def __init__(self, var):
        self.var = var
        self.virtual = True

    def __str__(self):
        return f"(virtual){self.var}"

    def compile4(self, context):
        return compile4_var(self.var.var_id, context)


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
        assert not self.expr.virtual

    def __str__(self):
        return f"Assign {self.var} <- {self.expr}"

    def compile5(self, context):
        return compile5_assign(self, context)

    def compile2(self, context):
        pass


class Assemble(ActionOpMixin):
    def __str__(self):
        return f"Assemble"

    def compile5(self, context):
        return compile5_assemble(context)

    def compile2(self, context):
        pass


class Call(ActionOpMixin):
    def __init__(self, layout):
        self.layout = layout


# Only unsigned integer constants are initialized as Const
# empty slice is the only slice constant that could be created currently
class Const(UniversalNumberOpMixin):
    def __init__(self, value):
        self.value = value
        self.virtual = False

    @staticmethod
    def wrap_int(value):
        if isinstance(value, int):
            return Const(value)
        else:
            return value

    def __str__(self):
        return f"Const({self.value})"

    def compile4(self, context):
        return compile4_const(self.value)


class NoData(SliceOpMixin):
    def __init__(self):
        self.virtual = False

    def __str__(self):
        return "EmptySlice"

    def compile4(self, context):
        return compile4_empty()


class Sequence:
    def __init__(
        self, meta, data, zero_based=True, data_len=Const(0), window=None,
    ):
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
        self.context = StackContext()
        self.layer_count = 0
        super().__init__()

    def handle_set(self, prototype):
        layer = Layer(prototype, self.context, self.layer_count)
        self.layer_count += 1
        return layer

    def __iadd__(self, dir_pred):
        dir_pred.src.layer.next_list.append((dir_pred.pred, dir_pred.dst.layer))
        return self


class Layer:
    def __init__(self, prototype, stack, layer_id):
        self.layer = compile3a_prototype(
            prototype, stack, layer_id, EventGroup({}, {}, {})
        )
        self.header = ForeignNameMap(self.layer.header, self.layer.context)
        if self.layer.temp is not None:
            self.temp = ForeignNameMap(self.layer.temp, self.layer.context)
        if self.layer.perm is not None:
            self.perm = ForeignNameMap(self.layer.perm, self.layer.context)
        self.event = self.layer.event

    def __rshift__(self, dst_layer):
        return Direction(self, dst_layer)


class ForeignNameMap(NameMapMixin):
    def __init__(self, provider, context):
        self.name_map = provider.name_map
        self.context = context
        super().__init__()

    def handle_get(self, var):
        return ForeignVar(self.context.query(var))


class ForeignVar(UniversalNumberOpMixin):
    def __init__(self, reg):
        self.reg = reg
        self.virtual = False

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


Pred = Predicate


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
        self.virtual = False

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

        self.trans_var = Bit(16)

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
                self.accept_list.append(state.state_id)
            self.state_map[state.state_id] = []
        self.state_list = states
        super().__init__()

    def states(self):
        return self.state_list

    def handle_set(self, dir_pred):
        trans = PSMTrans(dir_pred.pred, dir_pred.dst.state_id, dir_pred.action)
        self.trans_list.append(trans)
        trans_id = len(self.trans_list)  # count from 1, 0 means not triggered yet
        self.state_map[dir_pred.src.state_id].append(trans_id)
        return trans_id

    def handle_get(self, trans_id):
        return self.trans_var == trans_id

    def compile0(self, state):
        return Action(
            [
                Assign(self.trans_var, 0),
                *[
                    If(self.trans_var == 0)
                    >> (
                        If(state == state_id)
                        >> self.compile0_trans_list(trans_list, state)
                    )
                    for state_id, trans_list in self.state_map.items()
                ],
            ]
        )

    def compile0_trans_list(self, trans_list, state):
        action = Action([])
        for trans_id in trans_list:
            trans = self.trans_list[trans_id - 1]
            action += If(self.trans_var == 0) >> (
                If(trans.pred)
                >> (
                    Assign(self.trans_var, trans_id)
                    + Assign(state, trans.dst_state)
                    + trans.action
                )
            )
        return action

    def compile0_accept_pred(self, state):
        pred = Const(0)
        for state_id in self.accept_list:
            pred = (state == state_id) | pred
        return pred


class PSMTrans:
    def __init__(self, pred, dst_state, action):
        self.pred = pred
        self.dst_state = dst_state
        self.action = action


class EventGroup(NameMapMixin):
    def __init__(self, name_map, cause_map, before_map):
        self.name_map = name_map
        self.cause_map = cause_map
        self.before_map = before_map
        super().__init__()

    def __iadd__(self, relation):
        if isinstance(relation, tuple):
            first, second = relation
            self.before_map[second].add(first)
        else:
            self.cause_map[relation.dst].add(relation.src)
        return self

    def handle_set(self, if_stat):
        event = Event(if_stat.pred, if_stat.yes_action)
        self.cause_map[event] = set()
        self.before_map[event] = set()
        return event

    def compile0(self, event_var_map):
        action = Action([])
        event_set = set(self.name_map.values())
        while event_set != set():
            free_event = next(
                event
                for event in event_set
                if not any(
                    before_event in event_set
                    for before_event in self.before_map[event] | self.cause_map[event]
                )
            )
            action += free_event.compile0(
                event_var_map[free_event],
                {event_var_map[event] for event in self.cause_map[free_event]},
            )
            event_set.remove(free_event)
        return action


class Event:
    def __init__(self, pred, action):
        self.pred = pred
        self.action = action

    def __rshift__(self, other):
        return Direction(self, other)

    def compile0(self, event_var, cause_vars):
        action = If(self.pred) >> (Assign(event_var, 1) + self.action)
        for var in cause_vars:
            action = If(var == 1) >> action
        return action


# Op
class HeaderContainOp(NumberOpMixin):
    def __init__(self, layout):
        self.layout = layout
        self.virtual = False

    def compile4(self, context):
        return compile4_header_contain(self.layout, context)


class Op2VirtualMixin:
    @property
    def virtual(self):
        return self.expr1.virtual or self.expr2.virtual


class AddOp(NumberOpMixin, Op2VirtualMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) + ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("add", self.expr1, self.expr2, context)


class LogicalOrOp(NumberOpMixin, Op2VirtualMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) or ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("or", self.expr1, self.expr2, context)


class SubOp(NumberOpMixin, Op2VirtualMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) - ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("sub", self.expr1, self.expr2, context)


class LeftShiftOp(NumberOpMixin, Op2VirtualMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) << ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("left_shift", self.expr1, self.expr2, context)


class LessThanOp(NumberOpMixin, Op2VirtualMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) < ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("less_than", self.expr1, self.expr2, context)


class EqualOp(NumberOpMixin, Op2VirtualMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) == ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("equal", self.expr1, self.expr2, context)


class LogicalAndOp(NumberOpMixin, Op2VirtualMixin):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __str__(self):
        return f"({self.expr1}) and ({self.expr2})"

    def compile4(self, context):
        return compile4_op2("and", self.expr1, self.expr2, context)


class SliceBeforeOp(SliceOpMixin, Op2VirtualMixin):
    def __init__(self, slice, index):
        self.slice = slice
        self.index = index

    def __str__(self):
        return f"({self.slice})[:{self.index}]"

    def compile4(self, context):
        return compile4_op2("slice_before", self.slice, self.index, context)


class SliceAfterOp(SliceOpMixin, Op2VirtualMixin):
    def __init__(self, slice, index):
        self.slice = slice
        self.index = index

    def __str__(self):
        return f"({self.slice})[{self.index}:]"

    def compile4(self, context):
        return compile4_op2("slice_after", self.slice, self.index, context)


class SliceGetOp(NumberOpMixin, Op2VirtualMixin):
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
        self.virtual = self.slice.virtual

    def __str__(self):
        return f"({self.slice}).length"

    def compile4(self, context):
        return compile4_op1("slice_length", self.slice, context)


class NotOp(NumberOpMixin):
    def __init__(self, expr):
        self.expr = expr
        self.virtual = self.expr.virtual

    def __str__(self):
        return f"not ({self.expr})"

    def compile4(self, context):
        return compile4_op1("not", self.expr, context)


class PayloadExpr(SliceOpMixin):
    def __init__(self):
        self.virtual = False

    def __str__(self):
        return "payload"

    def compile4(self, context):
        return compile4_payload()


class TotalExpr(SliceOpMixin):
    def __init__(self):
        self.virtual = False

    def __str__(self):
        return "total"

    def compile4(self, context):
        return compile4_total()


class ContentExpr(SliceOpMixin):
    def __init__(self):
        self.virtual = False

    def __str__(self):
        return "sdu"

    def compile4(self, context):
        return compile4_content(context)
