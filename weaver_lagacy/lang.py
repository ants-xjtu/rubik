from weaver.lang2 import Variable, Predefined, Sequence as BaseSequence, IsParsed
from weaver.lang2.op import (
    Assign,
    LogicalNot,
    Payload,
    Total,
    SliceLength,
    Assemble,
    EmptySlice as NoData,
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

        self.v = None  # todo

    def header_contain(self, layout):
        return IsParsed(layout)


class If:
    def __init__(self, pred):
        self.pred = pred


class Else:
    pass


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


def make_psm_state(count):
    return tuple([PSMState() for i in range(count)])


class PSM:
    def __init__(self, *state_list):
        self.state_list = state_list

    def states(self):
        return self.state_list
