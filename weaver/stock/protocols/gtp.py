# pylint: disable = unused-wildcard-import
from weaver.lang import *


def gtp():
    proto = ProtoCore()

    has_exthdr = HeaderRegProto(StructRegAux(1, 1))
    has_seqnum = HeaderRegProto(StructRegAux(1, 1))
    has_npdunum = HeaderRegProto(StructRegAux(1, 1))

    parser_core = HeaderParser.parse(proto, Layout({
        'version': HeaderRegProto(StructRegAux(1, 3)),
        'protocol': HeaderRegProto(StructRegAux(1, 1)),
        '_1': HeaderRegProto(StructRegAux(1, 1)),
        'has_exthdr': has_exthdr,
        'has_seqnum': has_seqnum,
        'has_npdunum': has_npdunum,
        'msgtype': HeaderRegProto(StructRegAux(1)),
        'length': HeaderRegProto(StructRegAux(2)),
        'teid': HeaderRegProto(StructRegAux(4)),
        'optional': HeaderRegProto(ByteSliceRegAux(
            Expr(
                [has_exthdr, has_npdunum, has_seqnum],
                '({0} == 1 || {1} == 1 || {2} == 1) * 3'
            )
        ))
    }))

    ext_length = HeaderRegProto(StructRegAux(1))
    ext_type = HeaderRegProto(RegAux(1))
    ext_layout = Layout({
        'length': ext_length,
        'content': HeaderRegProto(ByteSliceRegAux(Expr([ext_length], '({0} << 2) - 2'))),
    })
    parser = parser_core.then(
        HeaderParser.when(
            proto, Expr([
                parser_core.get('has_exthdr'),
                parser_core.get('has_npdunum'),
                parser_core.get('has_seqnum'),            
            ], '{0} == 1 || {1} == 1 || {2} == 1'),
            HeaderParser.tagged(
                proto, Expr(
                    [ext_type], '{0} != 0'
                ), ext_type, {
                    (0, 'nomore'): Layout({}),
                    (None, '_'): ext_layout},
            )))

    return Proto(proto, parser)
