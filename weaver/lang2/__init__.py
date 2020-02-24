from weaver.lang2.op import NumberOpMixin, SliceOpMixin


class Predefined:
    def __init__(self):
        self.state = Variable(1, None, None, 0)
        self.trans = Variable(2, None, None, None)
        self.reversed = Variable(1, None, None, None)


class Variable(NumberOpMixin, SliceOpMixin):
    def __init__(self, byte_length, bit_length, length_expr, initial_expr):
        self.byte_length = byte_length
        self.bit_length = bit_length
        self.length_expr = length_expr
        self.initial_expr = initial_expr


class Header:
    def __init__(self, layouts):
        self.layouts = layouts


class StaticLayout:
    def __init__(self, name_map):
        self.name_map = name_map


class ParseWhen:
    def __init__(self, pred, layouts):
        self.pred = pred
        self.layouts = layouts


class ParseLoopUntil:
    def __init__(self, tag_var, layout_map, pred):
        self.tag_var = tag_var
        self.layout_map = layout_map
        self.pred = pred


class IsParsed(NumberOpMixin):
    def __init__(self, layout):
        self.layout = layout


class SingleKey:
    def __init__(self, var_list):
        self.var_list = var_list


class DualKey:
    def __init__(self, var_list1, var_list2):
        self.var_list1 = var_list1
        self.var_list2 = var_list2


class Instance:
    def __init__(self, name_map):
        self.name_map = name_map


class Automatic:
    def __init__(self, name_map):
        self.name_map = name_map


class Sequence:
    def __init__(self, offset, data, takeup, window_left, window_size):
        self.offset = offset
        self.data = data
        self.takeup = takeup
        self.window_left = window_left
        self.window_size = window_size


class StateMachine:
    def __init__(self, state_map, accept_state):
        self.state_map = state_map
        self.accept_state = accept_state


class Trans:
    def __init__(self, pred, dest_state, action):
        self.pred = pred
        self.dest_state = dest_state
        self.action = action


class Event:
    def __init__(self, pred, action):
        self.pred = pred
        self.action = action


class EventMap:
    def __init__(self, name_map=None, before_map=None, cause_map=None):
        self.name_map = name_map or {}
        self.before_map = before_map or {}
        self.cause_map = cause_map or {}

    def add(self, name, event):
        self.name_map[name] = event
        self.before_map[name] = set()
        self.cause_map[name] = set()

    def before(self, prev, current):
        self.before_map[current].add(prev)

    def cause(self, prev, current):
        self.cause_map[current].add(prev)


class Prototype:
    def __init__(
        self,
        header,
        key,
        instance,
        automatic,
        general,
        sequence,
        state_machine,
        event_map,
    ):
        self.header = header
        self.key = key
        self.instance = instance
        self.automatic = automatic
        self.general = general
        self.sequence = sequence
        self.state_machine = state_machine
        self.event_map = event_map


class ForeignVariable:
    def __init__(self, layer, variable):
        self.layer = layer
        self.variable = variable


class Stack:
    def __init__(self, name_map, jump_map):
        self.name_map = name_map
        self.jump_map = jump_map


class Jump:
    def __init__(self, pred, dest_layer):
        self.pred = pred
        self.dest_layer = dest_layer
