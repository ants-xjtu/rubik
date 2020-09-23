# pylint: disable = unused-wildcard-import
from rubik.lang import *


def quic_header_protocol_parser(stack):
    class PacketType(layout):
        type = Bit(8)

    class Part1(layout):
        version = Bit(32)
        id_len = Bit(8)

    class DstConnID(layout):
        dstid = Bit((((Part1.id_len & 0xF0) >> 4) + 3) << 3)

    class SrcConnID(layout):
        srcid = Bit(((Part1.id_len & 0x0F) + 3) << 3)

    class Part2(layout):
        payload_length1 = Bit(8)

    class PayloadLengthTail(layout):
        payload_length2 = Bit(
            ((Const(1) << ((Part2.payload_length1 & 0xC0) >> 6)) - 1) << 3
        )

    class Part3(layout):
        packet_number = Bit(32)

    class ShortHeader(layout):
        dst_conn_id = Bit(stack.udp.perm.dst_conn_id_len << 3)
        # packet_number = \
        #     byte(1 << (QUICHeaderFormPacketType.header_form_packet_type & 0x03))
        packet_number = Bit(8)

    quic_header_protocol = ConnectionOriented()
    quic_header_protocol.header = PacketType
    long_header = Part1
    long_header += If(long_header.id_len & 0xF0 != 0) >> DstConnID
    long_header += If(long_header.id_len & 0x0F != 0) >> SrcConnID
    long_header += Part2
    long_header += If(long_header.payload_length1 & 0xC0 != 0) >> PayloadLengthTail
    long_header += Part3
    quic_header_protocol.header += (
        If(quic_header_protocol.header.type & 0x80 != 0) >> long_header
    )
    quic_header_protocol.header += (
        If(quic_header_protocol.header.type & 0x80 == 0) >> ShortHeader
    )
    quic_header_protocol.prep = If(
        quic_header_protocol.header_contain(Part1)
    ) >> Assign(
        stack.udp.perm.dst_conn_id_len,
        ((quic_header_protocol.header.id_len & 0xF0) >> 4) + 3,
    )

    # TODO: change to Connection ID
    quic_header_protocol.selector = (
        [stack.ip.header.saddr, stack.udp.header.src_port],
        [stack.ip.header.daddr, stack.udp.header.dst_port],
    )

    # TODO: drive this state machine with `quic_frame`'s packets
    start = PSMState(start=True, accept=True)
    quic_header_protocol.psm = PSM(start)

    quic_header_protocol.psm.loop = (start >> start) + Predicate(1)
    return quic_header_protocol
