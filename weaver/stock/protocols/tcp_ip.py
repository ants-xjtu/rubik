# pylint: disable = unused-wildcard-import
from weaver.lang import *
from weaver.code import *
from weaver.auxiliary import *
from weaver.writer import *


def ip():
    parser = HeaderParser.parse(Layout({
        'ver': RegProto(StructRegAux(1, 4)),
        'ihl': RegProto(StructRegAux(1, 4)),
        'tos': RegProto(StructRegAux(1)),
        'length': RegProto(StructRegAux(2)),
        'identifier': RegProto(StructRegAux(2)),
        '_1': RegProto(StructRegAux(1, 1)),
        'dont_frag': RegProto(StructRegAux(1, 1)),
        'more_frag': RegProto(StructRegAux(1, 1)),
        'offset_1': RegProto(StructRegAux(1, 5)),
        'offset_2': RegProto(StructRegAux(1)),
        'ttl': RegProto(StructRegAux(1)),
        'protocol': RegProto(StructRegAux(1)),
        'checksum': RegProto(StructRegAux(2)),
        'srcip': RegProto(StructRegAux(4)),
        'dstip': RegProto(StructRegAux(4)),
    }))

    data = SetupInst(Layout({
        'state': RegProto(StructRegAux(1)),
        'expr1': RegProto(StructRegAux(1)),
    }), {
        'expr1': Expr([parser.get('more_frag')], '{0} == 0'),
    })

    s_dump, s_frag = tuple(range(2))
    t_dump, t_more, t_frag, t_last = tuple(x + 1 for x in range(4))
    state_machine = StateMachine([
        TransMap(s_dump, {
            Expr([parser.get('dont_frag')], '{0} == 1'): TransDest(t_dump, s_dump, []),
            Expr([parser.get('more_frag')], '{0} == 1'): TransDest(t_more, s_frag, []),
        }),
        TransMap(s_frag, {
            Expr([data.get('expr1'), proto.seq_ready], '{0} == 1 && {1}'): TransDest(t_last, s_dump, []),
            Expr([data.get('expr1'), proto.seq_ready], '{0} == 0 || !{1}'): TransDest(t_frag, s_frag, []),
        })
    ])
    events = Events({
        'assemble': Event(Expr([data.get('state')], f'{{0}} == {s_dump}'), [
            ConstRaw(Command(sequence, 'Assemble', [], opt_target=True,
                             aux=InstrWriter(SeqAssembleWriter()))),
        ])
    })
