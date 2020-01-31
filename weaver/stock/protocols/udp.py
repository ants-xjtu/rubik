# pylint: disable = unused-wildcard-import
from weaver.lang import *


def udp():
    proto = ProtoCore()

    parser = HeaderParser.parse(proto, Layout({
        'srcport': HeaderRegProto(StructRegAux(2)),
        'dstport': HeaderRegProto(StructRegAux(2)),
        'length': HeaderRegProto(StructRegAux(2)),
        'checksum': HeaderRegProto(StructRegAux(2)),
    }))

    return Proto(proto, parser)
