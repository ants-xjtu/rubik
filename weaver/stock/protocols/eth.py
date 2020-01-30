# pylint: disable = unused-wildcard-import
from weaver.lang import *


def eth():
    proto = ProtoCore()

    parser = HeaderParser.parse(proto, Layout({
        'srcmac_1': HeaderRegProto(StructRegAux(2)),
        'srcmac_2': HeaderRegProto(StructRegAux(2)),
        'srcmac_3': HeaderRegProto(StructRegAux(2)),
        'dstmac_1': HeaderRegProto(StructRegAux(2)),
        'dstmac_2': HeaderRegProto(StructRegAux(2)),
        'dstmac_3': HeaderRegProto(StructRegAux(2)),
        'protocol': HeaderRegProto(StructRegAux(2)),
    }))

    auto = SetupAuto({
        'h_protocol': RegProto(RegAux(2)),
    })

    general = [
        Assign(auto.get('h_protocol'), Expr([parser.get('protocol')], 'WV_NToH16({0})')),
    ]

    return Proto(proto, parser, setup_auto=auto, general=general)
