from weaver.code import Value, AggValue
from weaver.util import OpMixin


class ExprNode(OpMixin):
    def compile(self, symbol_table):
        raise NotImplementedError()

    @staticmethod
    def wrap_expr(expr):
        assert expr['type'] == 'bi'
        return BiExpr(expr['name'], expr['op1'], expr['op2'])


class VReg(ExprNode):
    def __init__(self, byte_len, bit_len=None, debug_name='<no name>'):
        super().__init__()
        self.byte_len = byte_len
        if bit_len is not None:
            assert byte_len == 1
        self.bit_len = bit_len
        self.debug_name = debug_name

    def compile(self, symbol_table):
        return Value([symbol_table[self]], '{0}')


class BiExpr(ExprNode):
    def __init__(self, op_name, op1, op2):
        super().__init__()
        self.op_name = op_name
        self.op1 = op1
        self.op2 = op2

    def compile(self, symbol_table):
        return AggValue([
            self.op1.compile(symbol_table), self.op2.compile(symbol_table)
        ], f'{{0}} {self.op_name} {{1}}')


class CallExpr(ExprNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def compile(self, symbol_table):
        compiled_args = [arg.compile(symbol_table) for arg in self.args]
        return AggValue([compiled_args], f'{self.name}({", ".join("{" + str(i) + "}" for i in range(len(compiled_args)))})')


class Seq:
    def __init__(self, offset: Value, data: Value, zero_base: bool = True,
                 takeup: Value = None, window_left: Value = None, window_right: Value = None):
        self.offset = offset
        self.data = data
        self.zero_base = zero_base
        self.takeup = takeup or Value([], '0')
        if window_left is not None:
            assert window_right is not None
            self.window = (window_left, window_right)
        else:
            self.window = (Value([], '0'), Value([], '0'))


class ProgramProto:
    def __init__(self, bi):
        self.bi = bi
        self.header = None
        self.key = None
        self.half_key1 = self.half_key2 = None
        self.seq = None
        # state machine
        # events


def connectionless():
    return ProgramProto(False)


def connection_oriented():
    return ProgramProto(True)


class _ParseHeaderStat:
    def __init__(self, field_map):
        self.field_map = field_map

    def add_stats(self, stat):
        return ParseActions([self, stat])

    def then_when(self, cond):
        outer_self = self

        class Helper:
            def select(self, tagged_layout):
                return outer_self.add_stats(ParseTaggedLoop(cond, tagged_layout))
        return Helper()


class ParseHeaderStat(_ParseHeaderStat):
    def __init__(self, field_map):
        super().__init__(field_map)

    def __getattr__(self, name):
        return getattr(super(), 'field_map')[name]


class ParseLayout(ParseHeaderStat):
    def __init__(self, layout):
        field_map = {name: field for name,
                     field in layout.__dict__ if not name.startswith('_')}
        super().__init__(field_map)
        self.layout = layout


class ParseTaggedLoop(ParseHeaderStat):
    def __init__(self, cond, tagged_layout):
        super().__init__({})
        self.cond = cond
        self.tagged_layout = tagged_layout


class ParseActions(ParseHeaderStat):
    def __init__(self, stats, field_map=None):
        field_map = field_map or {
            name: field for name, field in stat.field_map.items()
            for stat in stats
        }
        super().__init__(field_map)
        self.stats = stats

    def add_stats(self, stat):
        return ParseActions(self.stats + [stat], {**self.field_map, **stat.field_map})


def parse(*layouts):
    return ParseActions([ParseLayout(layout) for layout in layouts])


class LayoutField(VReg, OpMixin):
    def __init__(self, byte_length, bit_length, computed):
        super().__init__(byte_length, bit_length)
        self.computed = computed

    def compute(self, expr):
        return AutoField(self, True, expr)

    @staticmethod
    def wrap_expr(expr):
        # TODO
        return AutoField(None, False, expr)


class AutoField(LayoutField):
    def __init__(self, proto, computed, expr):
        super().__init__(proto.byte_length, proto.bit_length, computed)
        self.expr = expr


class U16(AutoField):
    def __init__(self):
        proto = Byte(2)
        super().__init__(proto, False, CallExpr('WV_NToH16', [proto]))


class U32(AutoField):
    def __init__(self):
        proto = Byte(4)
        super().__init__(proto, False, CallExpr('WV_NToH32', [proto]))


class Bit(LayoutField):
    def __init__(self, length):
        assert 0 < length < 8
        super().__init__(1, length, False)


class Byte(LayoutField):
    def __init__(self, length):
        assert length in [1, 2, 4, 8]
        super().__init__(length, None, False)


class Slice(LayoutField):
    def __init__(self, length_expr):
        super().__init__(None, None, False)
        self.length_expr = length_expr
