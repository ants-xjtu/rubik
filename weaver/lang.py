from weaver.code import Value


class Seq:
    def __init__(self, offset: Value, data: Value, zero_base: bool = True, takeup: Value = None, window_left: Value = None, window_right: Value = None):
        self.offset = offset
        self.data = data
        self.zero_base = zero_base
        self.takeup = takeup or Value([], '0')
        if window_left is not None:
            assert window_right is not None
            self.window = (window_left, window_right)
        else:
            self.window = None


def connectionless():
    return lambda: None


def parse(*args):
    return ...
