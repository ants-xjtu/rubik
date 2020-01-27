# pylint: disable = unused-wildcard-import
from weaver.code import *
from weaver.writer import *
from weaver.auxiliary import *
from weaver.pattern import Patterns


runtime = 0
reg_aux[runtime] = RegAux(abstract=True)
header_parser = 1
reg_aux[header_parser] = RegAux(abstract=True)
instance = 2
reg_aux[instance] = RegAux(abstract=True)


class TransDest:
    def __init__(self, trans_id, to_state, action):
        self.trans_id = trans_id
        self.to_state = to_state
        self.action = action

    def compile(self, proto, env):
        return [
            SetValue(env[proto.state], Value([], self.to_state)),
            SetValue(env[proto.trans], Value([], self.trans_id)),
            *self.action.compile(proto, env),
        ]


class TransMap:
    def __init__(self, from_state, trans_map):
        self.from_state = from_state
        self.trans_map = trans_map

    def compile(self, proto, env):
        return [
            If(EqualTest(env[proto.trans], Value([], '0')), [], [
                If(EqualTest(env[proto.state], Value([], self.from_state)), [
                    If(cond.compile(proto, env), dest.compile(proto, env))
                    for cond, dest in self.trans_map.items()
                ])
            ])
        ]


class StateMachine:
    def __init__(self, map_list):
        self.map_list = map_list

    def compile(self, proto, env):
        return [
            SetValue(env[proto.trans], Value([], '0')),
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

    def compile(self, proto, env):
        return [
            Command(instance, 'Prefetch', [
                    self.key], opt_target=True, aux=InstrAux(PrefetchInstWriter())),
            If(Value([instance], aux=InstExistWriter()), [
                Command(instance, 'Fetch', [], opt_target=True,
                        aux=InstrAux(FetchInstWriter())),
            ], [
                Command(instance, 'Create', [
                        self.key], opt_target=True, aux=InstrAux(CreateInstWriter())),
                *[
                    SetValue(inst_reg, AggValue(
                        [instance, reg_aux[inst_reg].init_value.compile(proto, env)], '{1}'))
                    for inst_reg in self.inst_struct.regs
                ]
            ]),
            *[
                If(cond.compile(proto, env), [
                    SetValue(vexpr_reg, Value([], '1')),
                ])
                for vexpr_reg, cond in self.vexpr_map
            ],
        ]
