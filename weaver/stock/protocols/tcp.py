# pylint: disable = unused-wildcard-import
from weaver.lang import *


def tcp(allocated_ip):
    proto = ProtoCore()

    ws = Layout({
        'length': HeaderRegProto(StructRegAux(1)),
        'value': HeaderRegProto(StructRegAux(1)),
    })
    fallback_length = HeaderRegProto(StructRegAux(1))

    parser_core = HeaderParser.parse(proto, Layout({
        'srcport': HeaderRegProto(StructRegAux(2)),
        'dstport': HeaderRegProto(StructRegAux(2)),
        'seqnum': HeaderRegProto(StructRegAux(4)),
        'acknum': HeaderRegProto(StructRegAux(4)),
        'hdrlen': HeaderRegProto(StructRegAux(1, 4)),
        '_1': HeaderRegProto(StructRegAux(1, 4)),
        'cwr': HeaderRegProto(StructRegAux(1, 1)),
        'ece': HeaderRegProto(StructRegAux(1, 1)),
        'urg': HeaderRegProto(StructRegAux(1, 1)),
        'ack': HeaderRegProto(StructRegAux(1, 1)),
        'psh': HeaderRegProto(StructRegAux(1, 1)),
        'rst': HeaderRegProto(StructRegAux(1, 1)),
        'syn': HeaderRegProto(StructRegAux(1, 1)),
        'fin': HeaderRegProto(StructRegAux(1, 1)),
        'wndsize': HeaderRegProto(StructRegAux(2)),
        'checksum': HeaderRegProto(StructRegAux(2)),
        'urgptr': HeaderRegProto(StructRegAux(2)),
    }))

    parser = parser_core.then(HeaderParser.tagged(
        proto,
        Expr([proto.parsed_length, proto.total_length, parser_core.get(
            'hdrlen')], '{0} < ({2} << 2) && {0} < {1}'),
        HeaderRegProto(RegAux(1)), {
            (0, 'eol'): Layout({}),
            (1, 'nop'): Layout({}),
            (2, 'mss'): Layout({
                'length': HeaderRegProto(StructRegAux(1)),
                'value': HeaderRegProto(StructRegAux(1)),
            }),
            (3, 'ws'): ws,
            (4, 'sackperm'): Layout({
                'length': HeaderRegProto(StructRegAux(1)),
            }),
            (8, 'ts'): Layout({
                'length': HeaderRegProto(StructRegAux(1)),
                'value': HeaderRegProto(StructRegAux(4)),
                'echo_reply': HeaderRegProto(StructRegAux(4)),
            }),
            (12, 'ccnew'): Layout({
                'length': HeaderRegProto(StructRegAux(1)),
                'value': HeaderRegProto(StructRegAux(4)),
            }),
            (None, '_'): Layout({
                'length': fallback_length,
                'value': HeaderRegProto(ByteSliceRegAux(Expr([fallback_length], '({0} - 2) << 3'))),
            }),
        }))

    data = SetupInst(BiDataKey([
        allocated_ip.insert(allocated_ip.proto.parser.get('srcip')),
        parser.get('srcport'),
    ], [
        allocated_ip.insert(allocated_ip.proto.parser.get('dstip')),
        parser.get('dstport'),
    ]), {
        'act_lwnd': RegProto(InstRegAux(4, ConstRaw(zero))),
        'pas_lwnd': RegProto(InstRegAux(4, ConstRaw(zero))),
        'act_wscale': RegProto(InstRegAux(4, ConstRaw(zero))),
        'pas_wscale': RegProto(InstRegAux(4, ConstRaw(zero))),
        'act_wndsize': RegProto(InstRegAux(4, ConstRaw(Value([], f'{1 << 32 - 1}')))),
        'pas_wndsize': RegProto(InstRegAux(4, ConstRaw(Value([], f'{1 << 32 - 1}')))),
        'fin_seqnum1': RegProto(InstRegAux(4, ConstRaw(zero))),
        'fin_seqnum2': RegProto(InstRegAux(4, ConstRaw(zero))),
    })

    vdata = SetupVExpr({
        'expr1': EqualExpr(parser.get('ack'), ConstRaw(one)),
        'expr2': EqualExpr(parser.get('fin'), ConstRaw(one)),
        'expr3': Expr(
            [parser.get('ack'), parser.get('fin'), data.get(
                'fin_seqnum1'), parser.get('acknum')],
            '{0} == 1 && {1} == 0 && {2} + 1 == {3}',
        ),
        'expr4': Expr(
            [parser.get('ack'), parser.get('fin'), data.get(
                'fin_seqnum1'), parser.get('acknum')],
            '{0} == 1 && {1} == 1 && {2} + 1 == {3}',
        ),
        'expr5': Expr(
            [parser.get('ack'), data.get('fin_seqnum2'), parser.get('acknum')],
            '{0} == 1 && {1} + 1 == {2}',
        ),
    })

    auto = SetupAuto({
        'lwnd': RegProto(RegAux(4)),
        'wndsize': RegProto(RegAux(4)),
        'takeup': RegProto(RegAux(4)),
    })

    s_hs0, s_hs1, s_hs2, s_est, s_wv1, s_wv2, s_wv3, s_end = tuple(range(8))

    general = [
        When(Expr(
            [parser.get('syn'), parser.get('ack'), parser.get('fin')],
            '({0} == 1 && {1} == 0) || {2} == 1'
        ), [
            Assign(auto.get('takeup'), Expr(
                [proto.payload], '{0}.length + 1')),
        ], [
            Assign(auto.get('takeup'), Expr([proto.payload], '{0}.length')),
        ]),
        When(EqualExpr(parser.get('fin'), ConstRaw(one)), [
            When(EqualExpr(proto.state, ConstRaw(Value([], str(s_est)))), [
                Assign(
                    data.get('fin_seqnum1'),
                    Expr([parser.get('seqnum'), proto.payload],
                         '{0} + {1}.length')
                )
            ], [
                Assign(data.get('fin_seqnum2'), parser.get('seqnum')),
            ])
        ], [])
    ]

    def update_wnd(that_lwnd, that_wscale, that_wndsize, this_lwnd, this_wscale, this_wndsize):
        return [
            When(parser.contain('ws'), [
                Assign(that_wscale, parser.get('ws.value')),
            ], []),
            Assign(that_wndsize, parser.get('wndsize')),
            Assign(that_lwnd, parser.get('seqnum')),
            Assign(auto.get('wndsize'), Expr(
                [this_wndsize, this_wscale], '{0} << {1}')),
            Assign(auto.get('lwnd'), this_lwnd),
        ]

    general += [
        When(
            proto.to_active,
            update_wnd(
                data.get('pas_lwnd'), data.get(
                    'pas_wscale'), data.get('pas_wndsize'),
                data.get('act_lwnd'), data.get(
                    'act_wscale'), data.get('act_wndsize'),
            ),
            update_wnd(
                data.get('act_lwnd'), data.get(
                    'act_wscale'), data.get('act_wndsize'),
                data.get('pas_lwnd'), data.get(
                    'pas_wscale'), data.get('pas_wndsize'),
            )
        )
    ]

    seq = SeqProto(
        parser.get('seqnum'), proto.payload, False, auto.get('takeup'),
        (auto.get('lwnd'), Expr(
            [auto.get('lwnd'), auto.get('wndsize')], '{0} + {1}'))
    )

    t_null, t_hs1, t_hs2, t_est0, t_hs3, t_est, t_wv1, t_wv2, t_wv23, t_wv3, t_wv4 = tuple(
        x + 1 for x in range(11))

    def reset(from_state):
        return {
            Expr([parser.get('rst')], '{0} == 1'): TransDest(11 + from_state, s_end, []),
        }

    state_machine = StateMachine([
        TransMap(s_hs0, {
            **reset(s_hs0),
            Expr(
                [parser.get('syn'), parser.get('ack')],
                '{0} == 1 && {1} == 0'
            ): TransDest(t_hs1, s_hs1, []),
            Expr(
                [parser.get('syn'), parser.get('ack')],
                '{0} == 0 || {1} == 1'
            ): TransDest(t_null, s_end, []),
        }),
        TransMap(s_hs1, {
            **reset(s_hs1),
            Expr(
                [proto.to_active, parser.get('syn'), parser.get('ack')],
                '{0} == 1 && {1} == 1 && {2} == 1',
            ): TransDest(t_hs2, s_hs2, []),
        }),
        TransMap(s_hs2, {
            **reset(s_hs2),
            vdata.vexpr('expr1'): TransDest(t_hs3, s_est, []),
            vdata.zexpr('expr2'): TransDest(t_est0, s_hs2, []),
        }),
        TransMap(s_est, {
            **reset(s_est),
            vdata.zexpr('expr2'): TransDest(t_est, s_est, []),
            vdata.vexpr('expr2'): TransDest(t_wv1, s_wv1, []),
        }),
        TransMap(s_wv1, {
            **reset(s_wv1),
            vdata.vexpr('expr3'): TransDest(t_wv2, s_wv2, []),
            vdata.vexpr('expr4'): TransDest(t_wv23, s_wv3, []),
            # zexpr3 || zexpr4
        }),
        TransMap(s_wv2, {
            **reset(s_wv2),
            vdata.vexpr('expr2'): TransDest(t_wv3, s_wv3, []),
        }),
        TransMap(s_wv3, {
            **reset(s_wv3),
            vdata.vexpr('expr5'): TransDest(t_wv4, s_end, []),
        })
    ], {s_end})

    events = Events({
        'assemble': Event(Expr(
            [proto.trans],
            f'{{0}} == {t_est0} || {{0}} == {t_est} || {{0}} == {t_wv1}',
            f'{{0}} == {t_est0} or {{0}} == {t_est} or {{0}} == {t_wv1}',
        ), [
            seq.assemble(),
        ])
    }, {}, {})

    return Proto(proto, parser, data, vdata, auto, general, seq, state_machine, events)
