# pylint: disable = unused-wildcard-import
from weaver.code import *
from weaver.writer import *
from weaver.auxiliary import *
from weaver.header import *
from weaver.pattern import Patterns
from weaver.util import flatten


runtime = 0
reg_aux[runtime] = RegAux(abstract=True)
header_parser = 1
reg_aux[header_parser] = RegAux(abstract=True)
instance = 2
reg_aux[instance] = RegAux(abstract=True)

zero = Value([], '0')
one = Value([], '1')


class TransDest:
    def __init__(self, trans_id, to_state, actions):
        self.trans_id = trans_id
        self.to_state = to_state
        self.actions = actions

    def compile_l(self, proto, env):
        return [
            SetValue(env[proto.state], Value([], self.to_state)),
            SetValue(env[proto.trans], Value([], self.trans_id)),
            *[action.compile(proto, env) for action in self.actions],
        ]


class TransMap:
    def __init__(self, from_state, trans_map):
        self.from_state = from_state
        self.trans_map = trans_map

    def compile(self, proto, env):
        return (
            If(EqualTest(env[proto.trans], zero), [], [
                If(EqualTest(env[proto.state], Value([], self.from_state)), [
                    If(cond.compile(proto, env), dest.compile_l(proto, env))
                    for cond, dest in self.trans_map.items()
                ])
            ])
        )


class StateMachine:
    def __init__(self, map_list):
        self.map_list = map_list

    def compile_l(self, proto, env):
        return [
            SetValue(env[proto.trans], zero),
            *[
                trans_map.compile(proto, env)
                for trans_map in self.map_list
            ]
        ]


class SetupInst:
    def __init__(self, inst_struct, vexpr_map):
        aux = inst_struct.create_aux()
        if isinstance(aux, DataStructAux):
            self.key = Value(aux.key_regs)
        else:
            self.key = Value(aux.half_key1 + aux.half_key2)
        self.inst_struct = inst_struct
        self.vexpr_map = vexpr_map

    def compile_l(self, proto, env):
        return [
            Command(instance, 'Prefetch', [
                    self.key], opt_target=True, aux=InstrAux(PrefetchInstWriter())),
            If(Value([instance], aux=ValueAux(InstExistWriter())), [
                Command(instance, 'Fetch', [], opt_target=True,
                        aux=InstrAux(FetchInstWriter())),
                *[
                    SetValue(inst_reg, Value([instance]),
                             aux=InstrAux(NoneWriter()))
                    for inst_reg in self.inst_struct.regs
                ],
                SetValue(env[proto.to_active], Value(
                    [instance], aux=ValueAux(ToActiveWriter()))),
            ], [
                Command(
                    instance, 'Create', [self.key], opt_target=True, aux=InstrAux(CreateInstWriter())),
                *[
                    SetValue(inst_reg, AggValue(
                        [instance, reg_aux[inst_reg].init_value.compile(proto, env)], '{1}'))
                    for inst_reg in self.inst_struct.regs
                ],
                SetValue(env[proto.to_active], zero),
            ]),
            SetValue(sequence, Value([instance]), aux=InstrAux(NoneWriter())),
            *[
                If(cond.compile(proto, env), [
                    SetValue(vexpr_reg.compile(proto, env), Value([], '1')),
                ])
                for vexpr_reg, cond in self.vexpr_map
            ],
        ]


class Seq:
    def __init__(self, offset: Value, data: Value, zero_base: bool = True,
                 takeup: Value = None, window_left: Value = None, window_right: Value = None):
        self.offset = offset
        self.data = data
        self.zero_base = zero_base
        self.takeup = takeup or zero
        if window_left is not None:
            assert window_right is not None
            self.window = (window_left, window_right)
        else:
            self.window = (zero, zero)

    def compile(self, proto, env):
        return (
            Command(sequence, 'Insert', [
                self.offset, self.data, self.takeup, AggValue(
                    [self.window[0], self.window[1]])
            ], opt_target=True, aux=InstrAux(InsertWriter())),
        )


class ConstRaw:
    def __init__(self, compiled):
        self.compiled = compiled

    def compile(self, proto, env):
        return self.compiled


class Event:
    def __init__(self, cond, actions):
        self.cond = cond
        self.actions = actions

    def compile(self, proto, env):
        return (
            If(self.cond.compile(proto, env), [
               action.compile(proto, env) for action in self.actions]),
        )


class Events:
    def __init__(self, event_map):
        self.event_map = event_map

    def compile_l(self, proto, env):
        return [
            event.compile(proto, env)
            for event in self.event_map.values()
        ]


class RegProto:
    def __init__(self, aux):
        self.aux = aux

    def alloc(self, env):
        env[self] = reg_aux.alloc(self.aux)

    def compile(self, proto, env):
        return Value([env[self]], '{0}')


class Expr:
    def __init__(self, nodes, template):
        self.nodes = nodes
        self.template = template

    def compile(self, proto, env):
        return AggValue([node.compile(proto, env) for node in self.nodes], self.template)


class Layout:
    def __init__(self, reg_map):
        self.reg_map = reg_map

    def deconstruct(self, proto, env):
        actions = []
        current = Struct([], HeaderStructAux.create)
        current_byte = []
        for reg in self.reg_map.values():
            if reg.aux.byte_len is not None:
                if reg.aux.bit_len is None:
                    current.regs.append(env[reg])
                else:
                    current_byte.append(reg)
                    total_bits = sum(
                        bit_reg.aux.bit_len for bit_reg in current_byte)
                    assert total_bits <= 8
                    if total_bits == 8:
                        current_byte.reverse()
                        current.regs.extend(env[reg] for reg in current_byte)
                        current_byte = []
            else:
                assert reg.aux.bit_len is None
                if current.regs != []:
                    actions.append(LocateStruct(current))
                    current = Struct([], HeaderStructAux.create)
                actions.append(ParseByteSlice(
                    env[reg], reg.length_expr.compile(proto, env)))
        if current.regs != []:
            actions.append(LocateStruct(current))
        assert current_byte == []
        return actions

    def alloc(self, env):
        for reg in self.reg_map.values():
            reg.alloc(env)


class HeaderParser:
    def __init__(self, actions, reg_map):
        self.actions = actions
        self.reg_map = reg_map

    @staticmethod
    def parse(layout):
        return HeaderParser(layout.deconstruct(), layout.reg_map)

    def get(self, name):
        return self.reg_map[name]
