# pylint: disable = unused-wildcard-import
from weaver.lang import *


def ip():
    proto = ProtoCore()

    parser = HeaderParser.parse(proto, Layout({
        'ver': HeaderRegProto(StructRegAux(1, 4)),
        'ihl': HeaderRegProto(StructRegAux(1, 4)),
        'tos': HeaderRegProto(StructRegAux(1)),
        'length': HeaderRegProto(StructRegAux(2)),
        'identifier': HeaderRegProto(StructRegAux(2)),
        '_1': HeaderRegProto(StructRegAux(1, 1)),
        'dont_frag': HeaderRegProto(StructRegAux(1, 1)),
        'more_frag': HeaderRegProto(StructRegAux(1, 1)),
        'offset_1': HeaderRegProto(StructRegAux(1, 5)),
        'offset_2': HeaderRegProto(StructRegAux(1)),
        'ttl': HeaderRegProto(StructRegAux(1)),
        'protocol': HeaderRegProto(StructRegAux(1)),
        'checksum': HeaderRegProto(StructRegAux(2)),
        'srcip': HeaderRegProto(StructRegAux(4)),
        'dstip': HeaderRegProto(StructRegAux(4)),
    }))

    data = SetupInst(DataKey([
        parser.get('srcip'),
        parser.get('dstip'),
    ]), {
        #
    }, {
        'expr1': Expr([parser.get('more_frag')], '{0} == 0'),
    })

    auto = SetupAuto({
        'h_length': RegProto(RegAux(2)),
        'offset': RegProto(RegAux(2)),
        'length': RegProto(RegAux(2)),
    })

    general = [
        Assign(auto.get('h_length'), Expr(
            [parser.get('length')], 'WV_NToH16({0})')),
        Assign(auto.get('offset'), Expr(
            [parser.get('offset_1'), parser.get('offset_2')], '({0} << 8) + {1}')),
        Assign(auto.get('length'), Expr(
            [auto.get('h_length'), parser.get('ihl')], '{0} - ({1} << 2)')),
    ]

    seq = SeqProto(auto.get('offset'), Expr(
        [proto.payload, auto.get('length')], 'WV_SliceBefore({0}, {1})'))

    s_dump, s_frag = tuple(range(2))
    t_dump, t_more, t_frag, t_last = tuple(x + 1 for x in range(4))
    state_machine = StateMachine([
        TransMap(s_dump, {
            EqualExpr(parser.get('dont_frag'), ConstRaw(one)): TransDest(t_dump, s_dump, []),
            EqualExpr(parser.get('more_frag'), ConstRaw(one)): TransDest(t_more, s_frag, []),
        }),
        TransMap(s_frag, {
            data.vexpr('expr1'): TransDest(t_last, s_dump, []),
            data.zexpr('expr1'): TransDest(t_frag, s_frag, []),
        })
    ], {s_dump})

    events = Events({
        'assemble': Event(EqualExpr(proto.state, ConstRaw(Value([], str(s_dump)))), [
            seq.assemble(),
        ])
    }, {}, {})

    return Proto(proto, parser, data, auto, general, seq, state_machine, events)
