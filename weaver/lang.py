# pylint: disable = unused-wildcard-import
from weaver.code import *
from weaver.writer import *
from weaver.auxiliary import *
from weaver.header import *
from weaver.pattern import Patterns
from weaver.util import flatten


zero = Value([], '0')
one = Value([], '1')


class TransDest:
    def __init__(self, trans_id, to_state, actions):
        self.trans_id = trans_id
        self.to_state = to_state
        self.actions = actions

    def compile_l(self, proto, env):
        return [
            SetValue(proto.state.reveal(env), Value([], str(self.to_state))),
            SetValue(proto.trans.reveal(env), Value([], str(self.trans_id))),
            *[action.compile(proto, env) for action in self.actions],
        ]


class TransMap:
    def __init__(self, from_state, trans_map):
        self.from_state = from_state
        self.trans_map = trans_map

    def compile(self, proto, env):
        return (
            If(EqualTest(proto.trans.reveal(env), zero), [
                If(EqualTest(proto.state.reveal(env), Value([], str(self.from_state))), [
                    If(cond.compile(proto, env), dest.compile_l(proto, env))
                    for cond, dest in self.trans_map.items()
                ])
            ], [])
        )


class StateMachine:
    def __init__(self, map_list, accept_set):
        self.map_list = map_list
        self.accept_set = accept_set

    def compile_l(self, proto, env):
        return [
            SetValue(proto.trans.reveal(env), zero),
            *[
                trans_map.compile(proto, env)
                for trans_map in self.map_list
            ]
        ]

    def compile_accept(self, proto, env, next_codes):
        return (
            If(AggValue(
                [proto.state.compile(proto, env)],
                ' || '.join(f'{{0}} == {state}' for state in self.accept_set)
            ), next_codes)
        )


class DataKey:
    def __init__(self, regs):
        self.regs = regs

    def get_aux_creator(self, proto, env):
        return DataStructAuxCreator([reg.reveal(env) for reg in self.regs])

    def get_key(self, proto, env):
        return AggValue([reg.compile(proto, env) for reg in self.regs])


class BiDataKey:
    def __init__(self, half_key1, half_key2):
        self.half_key1 = half_key1
        self.half_key2 = half_key2

    def get_aux_creator(self, proto, env):
        return BiDataStructAuxCreator(
            [reg.reveal(env) for reg in self.half_key1],
            [reg.reveal(env) for reg in self.half_key2],
        )

    def get_key(self, proto, env):
        return AggValue([reg.compile(proto, env) for reg in self.half_key1 + self.half_key2])


class SetupVExpr:
    def __init__(self, vexpr_map):
        self.vexpr_map = vexpr_map
        self.vexpr_regs = {name: RegProto(InstRegAux(1, ConstRaw(zero)))
                           for name in self.vexpr_map}

    def vexpr(self, name):
        return Expr(
            [
                self.vexpr_regs[name], 
                self.vexpr_map[name],
                ConstRaw(Value([sequence], aux=ValueAux(SeqReadyWriter())))
            ], 
            'WV_UpdateV(&{0}, {1}) == 1 && {2} == 1'
        )

    def zexpr(self, name):
        return Expr(
            [
                self.vexpr_regs[name], 
                self.vexpr_map[name],
                ConstRaw(Value([sequence], aux=ValueAux(SeqReadyWriter())))
            ], 
            '!(WV_UpdateV(&{0}, {1}) == 1 && {2} == 1)'
        )

    def compile_l(self, proto, env):
        return [
            If(cond.compile(proto, env), [
                SetValue(self.vexpr_regs[vexpr_reg].reveal(env), one),
            ])
            for vexpr_reg, cond in self.vexpr_map.items()
        ]


class SetupInst:
    def __init__(self, key, data_regs):
        self.key = key
        self.data_regs = data_regs

    def alloc_create_inst_struct(self, proto, env, extra=None):
        return Struct([
            reg.alloc(env, name) for name, reg in {**(extra or {}), **self.data_regs}.items()
        ], self.key.get_aux_creator(proto, env))

    def get(self, name):
        return self.data_regs[name]

    def compile_l(self, proto, env, inst_struct):
        key = self.key.get_key(proto, env)
        if isinstance(self.key, BiDataKey):
            to_active = ([
                SetValue(
                    proto.to_active.reveal(env),
                    Value([instance], aux=ValueAux(ToActiveWriter()))
                )
            ], [
                SetValue(proto.to_active.reveal(env), zero)
            ])
        else:
            to_active = ([], [])
        return [
            Command(
                instance, 'Prefetch', [key],
                opt_target=True, aux=InstrAux(PrefetchInstWriter())
            ),
            If(Value([instance], aux=ValueAux(InstExistWriter())), [
                Command(
                    instance, 'Fetch', [],
                    opt_target=True, aux=InstrAux(FetchInstWriter())
                ),
                *[
                    SetValue(
                        reg, Value([instance]),
                        aux=InstrAux(NoneWriter())
                    )
                    for reg in inst_struct.regs
                ],
                *to_active[0],
            ], [
                Command(
                    instance, 'Create', [key], opt_target=True, aux=InstrAux(CreateInstWriter())),
                *[
                    SetValue(
                        reg, AggValue([
                            Value([instance]), reg_aux[reg].init_value.compile(
                                proto, env)
                        ], '{1}')
                    )
                    for reg in inst_struct.regs
                ],
                *to_active[1],
            ]),
            SetValue(sequence, Value([instance]), aux=InstrAux(NoneWriter())),
        ]


class SeqProto:
    def __init__(self, offset, data, zero_base=True, takeup=None, window=(None, None)):
        self.offset = offset
        self.data = data
        self.zero_base = zero_base
        self.takeup = takeup
        self.window = window
        self.use_data = False
        self.assembled = False

    def assemble(self):
        self.assembled = True
        return ConstRaw(
            Command(
                sequence, 'Assemble', [],
                opt_target=True, aux=InstrAux(SeqAssembleWriter())
            )
        )

    def content(self):
        self.use_data = True
        return ConstRaw(Value([sequence], aux=ValueAux(ContentWriter())))

    def precompile(self, proto, env):
        return Seq(
            self.offset.compile(proto, env),
            self.data.compile(proto, env),
            self.zero_base,
            (self.takeup.compile(proto, env)
             if self.takeup is not None else None),
            (self.window[0].compile(proto, env)
             if self.window[0] is not None else None),
            (self.window[1].compile(proto, env)
             if self.window[1] is not None else None),
        )


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
            Command(
                sequence, 'Insert', [
                    self.offset, self.data, self.takeup,
                    AggValue([self.window[0], self.window[1]])
                ], opt_target=True, aux=InstrAux(InsertWriter())
            )
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


class Call:
    def __init__(self, name, arg_map):
        self.name = name
        self.arg_map = arg_map

    def compile(self, proto, env):
        for reg in self.arg_map:
            reg.alloc(env, '<arg>')
        codes = [
            SetValue(reg.reveal(env), expr.compile(proto, env))
            for reg, expr in self.arg_map.items()
        ] + [
            Command(
                runtime, 'Call', [
                    reg.compile(proto, env)
                    for reg in self.arg_map
                ],
                opt_target=True, aux=InstrAux(
                    CallWriter(self.name, [reg.reveal(env)
                                           for reg in self.arg_map])
                )
            )
        ]
        return If(one, codes)


class Events:
    def __init__(self, event_map, before_map, trigger_map):
        self.event_map = event_map
        self.before_map = before_map
        self.trigger_map = trigger_map
        self.event_regs = {
            name: RegProto(RegAux(1)) for name in self.event_map
        }

    def alloc(self, env):
        for name, reg in self.event_regs.items():
            reg.alloc(env, name)

    def compile_l(self, proto, env):
        # dirty hack
        for event in self.event_map:
            if event not in self.event_regs:
                self.event_regs[event] = RegProto(RegAux(1))
                self.event_regs[event].alloc(env, event)

        codes = [
            SetValue(self.event_regs[evt].reveal(env), zero)
            for evt in self.event_map
        ]
        uncompiled_events = list(self.event_map)
        while uncompiled_events != []:
            event = next(
                evt for evt in uncompiled_events
                if (
                    evt not in self.before_map or
                    all(
                        before_event not in uncompiled_events
                        for before_event in self.before_map[evt]
                    )
                )
            )
            uncompiled_events.remove(event)
            event_codes = (
                If(self.event_map[event].cond.compile(proto, env), [
                    SetValue(self.event_regs[event].reveal(env), one),
                    *[
                        action.compile(proto, env) for action in self.event_map[event].actions
                    ]
                ])
            )
            if event in self.trigger_map:
                trigger_cond = Value(
                    [
                        self.event_regs[evt].reveal(env)
                        for evt in self.trigger_map[event]
                    ],
                    ' || '.join(
                        f'{{{i}}}' for i in range(len(self.trigger_map[event]))
                    )
                )
                event_codes = If(trigger_cond, [event_codes])
            codes.append(event_codes)
        return codes


class RegProto:
    def __init__(self, aux):
        self.aux = aux

    def alloc(self, env, name):
        self.aux.debug_name = name
        env[self] = reg_aux.alloc(self.aux)
        return env[self]

    def compile(self, proto, env):
        return Value([self.reveal(env)], '{0}')

    def reveal(self, env):
        # print(self.aux.debug_name)
        return env[self]


class ForeignRegProto(RegProto):
    def __init__(self, reg_proto, env):
        super().__init__(reg_proto.aux)
        self.reg_proto = reg_proto
        self.env = env

    def reveal(self, env):
        return self.reg_proto.reveal(self.env)


class Expr:
    def __init__(self, nodes, template, eval_template=None):
        self.nodes = nodes
        self.template = template
        self.eval_template = eval_template or template

    def compile(self, proto, env):
        return AggValue(
            [node.compile(proto, env) for node in self.nodes],
            self.eval_template,
            ValueAux(AggValueWriter(self.template))
        )


class EqualExpr(Expr):
    def __init__(self, reg_proto, expr):
        super().__init__([reg_proto, expr], '{0} == {1}')
        self.reg_proto = reg_proto
        self.expr = expr

    def compile(self, proto, env):
        # print(env)
        if isinstance(self.reg_proto, HeaderRegProto):
            return super().compile(proto, env)
        return EqualTest(self.reg_proto.reveal(env), self.expr.compile(proto, env))


class Layout:
    def __init__(self, reg_map):
        self.reg_map = reg_map

    def deconstruct(self, proto, env):
        actions = []
        current = []
        current_byte = []
        for name, reg in self.reg_map.items():
            reg.alloc(env, name)
            if reg.aux.byte_len is not None:
                if reg.aux.bit_len is None:
                    current.append(reg.reveal(env))
                else:
                    current_byte.append(reg)
                    total_bits = sum(
                        bit_reg.aux.bit_len for bit_reg in current_byte
                    )
                    assert total_bits <= 8
                    if total_bits == 8:
                        current_byte.reverse()
                        current.extend(reg.reveal(env) for reg in current_byte)
                        current_byte = []
            else:
                assert isinstance(reg.aux, ByteSliceRegAux)
                if current != []:
                    actions.append(
                        LocateStruct(Struct(current, HeaderStructAux.create))
                    )
                    current = []
                actions.append(
                    ParseByteSlice(
                        reg.reveal(env), reg.aux.length_expr.compile(
                            proto, env)
                    )
                )
        if current != []:
            actions.append(
                LocateStruct(Struct(current, HeaderStructAux.create))
            )
        assert current_byte == []
        return actions


class HeaderParser:
    def __init__(self, actions, reg_map, struct_map):
        self.actions = actions
        self.reg_map = reg_map
        self.struct_map = struct_map

    @staticmethod
    def parse(proto, layout):
        return HeaderParser(layout.deconstruct(proto, proto.env), layout.reg_map, {})

    @staticmethod
    def tagged(proto, cond, tag, layout_map):
        action_map = {}
        reg_map = {}
        struct_map = {}
        tag_reg = tag.alloc(proto.env, '<layout tag>')
        for (tag_value, name), layout in layout_map.items():
            action_map[tag_value] = layout.deconstruct(proto, proto.env)
            if action_map[tag_value] != []:
                assert isinstance(action_map[tag_value][0], LocateStruct)
                struct_map[name] = action_map[tag_value][0].struct
            reg_map.update({
                f'{name}.{reg_name}': reg for reg_name, reg in layout.reg_map.items()
            })
        compiled_cond = cond.compile(proto, proto.env)
        return HeaderParser([TaggedParseLoop(compiled_cond, tag_reg, action_map)], reg_map, struct_map)

    @staticmethod
    def when(proto, cond, parser):
        return HeaderParser([
            OptionalActions(cond.compile(proto, proto.env), parser.actions)
        ], parser.reg_map, parser.struct_map)

    def get(self, name):
        # print(name)
        return self.reg_map[name]

    def then(self, parser):
        return HeaderParser(
            self.actions + parser.actions,
            {**self.reg_map, **parser.reg_map},
            {**self.struct_map, **parser.struct_map}
        )

    def contain(self, name):
        return ConstRaw(Value([header_parser], aux=ValueAux(HeaderContainWriter(self.struct_map[name]))))


class HeaderRegProto(RegProto):
    def __init__(self, aux):
        super().__init__(aux)

    def compile(self, proto, env):
        # print(self.aux.debug_name)
        return Value([header_parser, self.reveal(env)], '{1}')


class Assign:
    def __init__(self, reg_proto, expr):
        self.reg_proto = reg_proto
        self.expr = expr

    def compile(self, proto, env):
        return SetValue(self.reg_proto.reveal(env), self.expr.compile(proto, env))


class When:
    def __init__(self, cond, yes_codes, no_codes):
        self.cond = cond
        self.yes_codes = yes_codes
        self.no_codes = no_codes

    def compile(self, proto, env):
        return If(self.cond.compile(proto, env), [
            instr.compile(proto, env) for instr in self.yes_codes
        ], [
            instr.compile(proto, env) for instr in self.no_codes
        ])


class ProtoCore:
    def __init__(self):
        self.state = RegProto(InstRegAux(1, ConstRaw(zero)))
        self.trans = RegProto(RegAux(2))
        self.to_active = RegProto(RegAux(1))
        self.ready = ConstRaw(
            Value([sequence], aux=ValueAux(SeqReadyWriter())))
        self.payload = ConstRaw(
            Value([header_parser], aux=ValueAux(PayloadWriter())))
        self.parsed = ConstRaw(
            Value([header_parser], aux=ValueAux(ParsedWriter())))
        self.total = ConstRaw(
            Value([header_parser], aux=ValueAux(TotalWriter())))
        self.env = {}


class Proto:
    def __init__(self, core, parser, setup_inst=None, setup_vexpr=None, setup_auto=None, general=None, seq=None, state_machine=None, events=None):
        self.core = core
        self.parser = parser
        self.setup_inst = setup_inst
        self.setup_vexpr = setup_vexpr
        self.setup_auto = setup_auto
        self.general = general
        self.seq = seq
        self.state_machine = state_machine
        self.events = events or Events({}, {}, {})

    def alloc_bundle(self):
        env = dict(self.core.env)
        if self.setup_inst is not None:
            extra = {}
            if self.state_machine is not None:
                extra['state'] = self.core.state
            if self.setup_vexpr is not None:
                extra.update(self.setup_vexpr.vexpr_regs)
            inst_struct = \
                self.setup_inst.alloc_create_inst_struct(self.core, env, extra)
            if isinstance(self.setup_inst.key, BiDataKey):
                self.core.to_active.alloc(env, 'to_active')
        else:
            inst_struct = None
        if self.setup_auto is not None:
            self.setup_auto.alloc(env)
        if self.state_machine is not None:
            self.core.trans.alloc(env, 'trans')
        if self.events is not None:
            self.events.alloc(env)
        return AllocatedBundle(self, env, inst_struct)


class AllocatedBundle:
    def __init__(self, proto, env, inst_struct):
        self.proto = proto
        self.env = env
        self.inst_struct = inst_struct

    def compile_bundle(self, name, next_map=None):
        actions = self.proto.parser.actions
        env = self.env
        codes = [
            Command(
                header_parser, 'Parse', [],
                opt_target=True, aux=InstrAux(ParseHeaderWriter())
            ),
        ]
        if self.proto.setup_inst is not None:
            codes += self.proto.setup_inst.compile_l(
                self.proto.core, env, self.inst_struct
            )
        if self.proto.general is not None:
            codes += [
                instr.compile(self.proto.core, env) for instr in self.proto.general
            ]
        if self.proto.seq is not None:
            seq = self.proto.seq.precompile(self.proto.core, env)
            codes += [seq.compile(self.proto.core, env)]
        else:
            seq = None
        # if self.proto.setup_vexpr is not None:
        #     codes += self.proto.setup_vexpr.compile_l(self.proto.core, env)
        if self.proto.state_machine is not None:
            codes += self.proto.state_machine.compile_l(self.proto.core, env)
        if self.proto.events is not None:
            codes += self.proto.events.compile_l(self.proto.core, env)
        nexti = {}
        next_codes = []
        if next_map is not None:
            if self.proto.seq is not None and self.proto.seq.assembled:
                content = self.proto.seq.content()
            else:
                content = self.proto.core.payload
            for cond, followed in next_map.items():
                # print(cond)
                recursive = followed == name
                next_command = Command(
                    runtime, 'Next', [content.compile(self.proto.core, env)],
                    opt_target=True, aux=InstrAux(NextWriter(recursive))
                )
                nexti[next_command] = followed
                next_branch = [
                    If(cond.compile(self.proto.core, env), [
                        next_command,
                    ])
                ]
                if self.proto.setup_inst is not None:
                    destroy_inst = [
                        Command(
                            instance, 'Destroy', [], opt_target=True,
                            aux=InstrAux(DestroyInstWriter())
                        ),
                    ]
                else:
                    destroy_inst = []
                if not recursive:
                    next_codes += next_branch + destroy_inst
                else:
                    next_codes += destroy_inst + next_branch
            if self.proto.state_machine is not None:
                codes += [
                    self.proto.state_machine.compile_accept(
                        self.proto.core, env, next_codes
                    )
                ]
            else:
                codes += next_codes
        else:
            if self.proto.setup_inst is not None:
                destroy_inst = [
                    Command(
                        instance, 'Destroy', [], opt_target=True,
                        aux=InstrAux(DestroyInstWriter())
                    ),
                ]
                if self.proto.state_machine is not None:
                    codes += [
                        self.proto.state_machine.compile_accept(
                            self.proto.core, env, destroy_inst
                        )
                    ]
                else:
                    codes += destroy_inst
        return CompiledBundle(
            BasicBlock.from_codes(codes).optimize(Patterns(seq)),
            actions, self.inst_struct, seq,
            self.proto.seq.use_data if self.proto.seq is not None else False,
            nexti
        )

    def insert(self, reg_proto):
        return ForeignRegProto(reg_proto, self.env)


class CompiledBundle:
    def __init__(self, recurse, actions, inst_struct, seq, use_data, nexti_map):
        self.recurse = recurse
        self.actions = actions
        self.inst = inst_struct
        self.seq = seq
        self.use_data = use_data
        self.nexti_map = nexti_map

    def register_nexti(self, sum_map):
        for nexti in self.nexti_map:
            sum_map[nexti] = self.nexti_map[nexti]

    def execute_in(self, context):
        context.execute_block_recurse(
            self.recurse, self.actions, self.inst, self.seq, self.use_data
        )


class SetupAuto:
    def __init__(self, reg_map):
        self.reg_map = reg_map

    def alloc(self, env):
        # print(self.reg_map)
        for name, reg in self.reg_map.items():
            reg.alloc(env, name)

    def get(self, name):
        return self.reg_map[name]
