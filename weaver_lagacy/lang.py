from weaver.lang2 import (
    Variable,
    Predefined,
    Sequence as BaseSequence,
    IsParsed,
    StateMachine,
    Trans as BaseTrans,
    EventMap,
    Event,
)
from weaver.lang2.op import (
    Assign,
    LogicalNot,
    Payload,
    Total,
    SliceLength,
    Assemble,
    EmptySlice as NoData,
    Action,
    When as BaseWhen,
    NumberOpMixin,
    SliceOpMixin,
)


class layout:
    pass


class HeaderMap:
    def __init__(self, name_map):
        self.name_map = name_map

    def __getattr__(self, name):
        return getattr(super(), "name_map")[name]


class Bit(Variable):
    def __init__(self, width, const=None, init=None):
        if isinstance(width, int):
            if width % 8 == 0:
                byte_length = width // 8
                bit_length = None
            else:
                assert width < 8, "bit field is too wide"
                byte_length = 1
                bit_length = width
            length_expr = None
        else:
            byte_length = bit_length = None
            length_expr = width
        super().__init__(byte_length, bit_length, length_expr, init)
        self.const = const


class Slice(Variable):
    def __init__(self):
        super().__init__(None, None, None, None)


class ConnectionOriented:
    def __init__(self):
        self.header = self.temp = self.perm = None
        self.preprocess = self.seq = self.psm = None
        self.event = None  # todo

        predefined = Predefined()
        self.current_state = predefined.state
        self.to_active = predefined.reversed
        self.to_passive = LogicalNot(predefined.reversed)

        self.payload = self.cursor = Payload()
        self.payload_len = SliceLength(Payload())

        self.v = VProxy(self)

    def header_contain(self, layout):
        return IsParsed(layout)


class VProxy:
    def __init__(self, host):
        self.host = host

    @property
    def header(self):
        return VNameMap(self.host.header)

    @property
    def temp(self):
        return VNameMap(self.host.temp)


class VNameMap:
    def __init__(self, name_map):
        self.name_map = name_map

    def __getattr__(self, name):
        return VExprVar(getattr(getattr(super(), "name_map"), name))


class VExprVar(NumberOpMixin, SliceOpMixin):
    def __init__(self, var):
        self.var = var


class If:
    def __init__(self, pred):
        self.pred = pred

    def __rshift__(self, action):
        return When(self.pred, action, Action([]))


class When(BaseWhen):
    def __init__(self, pred, yes_action, no_action):
        super().__init__(pred, yes_action, no_action)

    def __rshift__(self, else_):
        assert isinstance(else_, Else), "invalid syntax"
        return ExpectNoAction(self)


class Else:
    pass


class ExpectNoAction:
    def __init__(self, when):
        self.when = when

    def __rshift__(self, no_action):
        return When(self.when.pred, self.when.yes_action, no_action)


class Predicate:
    def __init__(self, pred):
        self.pred = pred


class AnyUntil:
    def __init__(self, layout_list, pred):
        self.layout_list = layout_list
        self.pred = pred


class Sequence(BaseSequence):
    def __init__(self, meta, data, data_len, window=None):
        if window is None:
            window_left = window_size = None
        else:
            window_left, window_right = window
            window_size = window_right - window_left
        super().__init__(meta, data, data_len, window_left, window_size)


class PSMState:
    def __init__(self, start=False, accept=False):
        self.start = start
        self.accept = accept
        self.state_id = None

    def __rshift__(self, dest_state):
        return Trans(self.state_id, dest_state.state_id, None, Action([]))


class Trans:
    def __init__(self, src_state, dest_state, pred, action):
        self.src_state = src_state
        self.dest_state = dest_state
        self.pred = pred
        self.action = action

    def __add__(self, item):
        if isinstance(item, Predicate):
            assert self.pred is None
            return Trans(self.src_state, self.dest_state, item.pred, self.action)
        else:
            return Trans(self.src_state, self.dest_state, self.pred, self.action + item)


def make_psm_state(count):
    return tuple([PSMState() for i in range(count)])


class PSMImpl:
    def __init__(self, *state_list):
        state_count = 1  # 0 is reserved for start state
        accept_state = None
        for state in state_list:
            assert state.state_id is None, "PSM state already used"
            if state.start:
                state.state_id = 0
            else:
                state.state_id = state_count
                state_count += 1
            if state.accept:
                assert accept_state is None, "multiple accepted state is not support"
                accept_state = state.state_id
        self.state_list = state_list
        self.accept_state = accept_state
        self.state_map = {}
        self.trans_count = 0
        self.trans_map = {}

    def states(self):
        return self.state_list

    def add_trans(self, name, trans):
        if trans.src_state not in self.state_map:
            self.state_map[trans.src_state] = []
        self.state_map[trans.src_state].append(
            BaseTrans(trans.pred, trans.dest_state, trans.action)
        )
        self.trans_map[name] = self.trans_count + 1
        self.trans_count += 1

    def get_trans_id(self, name):
        return self.trans_map[name]


class PSM:
    def __init__(self, *state_list):
        setattr(super(), "impl", PSMImpl(*state_list))

    def __setattr__(self, name, trans):
        getattr(super(), "impl").add_trans(name, trans)

    def __getattr__(self, name):
        getattr(super(), "impl").get_trans_id(name)

    def states(self):
        return getattr(super(), "impl").states()


class EventManager:
    def __init__(self):
        setattr(super(), "impl", EventMap())
        setattr(super(), "name_map", {})

    def __setattr__(self, name, when):
        event = Event(when.pred, when.yes_action)
        getattr(super(), "impl").add(name, event)
        getattr(super(), "name_map")[name] = event

    def __getattr__(self, name):
        return getattr(super(), "name_map")[name]

