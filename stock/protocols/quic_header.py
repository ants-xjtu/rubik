from weaver.lang import *

def quic_header_protocol_parser(stack):
    class QUICHeaderFormPacketType(layout):
        header_form_packet_type = Bit(8)


    class QUICLongHeaderPart1(layout):
        version = Bit(32)
        dst_src_conn_id_len = Bit(8)


    class QUICLongHeaderOptionalDstConnID(layout):
        dst_conn_id = Bit(
            (((QUICLongHeaderPart1.dst_src_conn_id_len & 0xF0) >> 4) + 3) << 3
        )


    class QUICLongHeaderOptionalSrcConnID(layout):
        src_conn_id = Bit(((QUICLongHeaderPart1.dst_src_conn_id_len & 0x0F) + 3) << 3)


    class QUICLongHeaderPart2(layout):
        payload_length_first_byte = Bit(8)


    class QUICLongHeaderOptionalPayloadLengthTail(layout):
        payload_length_tail = Bit(
            (
                (Const(1) << ((QUICLongHeaderPart2.payload_length_first_byte & 0xC0) >> 6))
                - 1
            )
            << 3
        )


    class QUICLongHeaderPart3(layout):
        packet_number = Bit(32)


    class QUICShortHeader(layout):
        dst_conn_id = Bit(stack.udp.perm.dst_conn_id_len << 3)
        # packet_number = \
        #     byte(1 << (QUICHeaderFormPacketType.header_form_packet_type & 0x03))
        packet_number = Bit(8)

    quic_header_protocol = ConnectionOriented()
    quic_header_protocol.header = QUICHeaderFormPacketType
    long_header = QUICLongHeaderPart1
    long_header += (
        If(long_header.dst_src_conn_id_len & 0xF0 != 0) >> QUICLongHeaderOptionalDstConnID
    )
    long_header += (
        If(long_header.dst_src_conn_id_len & 0x0F != 0) >> QUICLongHeaderOptionalSrcConnID
    )
    long_header += QUICLongHeaderPart2
    long_header += (
        If(long_header.payload_length_first_byte & 0xC0 != 0)
        >> QUICLongHeaderOptionalPayloadLengthTail
    )
    long_header += QUICLongHeaderPart3
    quic_header_protocol.header += (
        If(quic_header_protocol.header.header_form_packet_type & 0x80 != 0) >> long_header
    )
    quic_header_protocol.header += (
        If(quic_header_protocol.header.header_form_packet_type & 0x80 == 0)
        >> QUICShortHeader
    )
    quic_header_protocol.prep = If(
        quic_header_protocol.header_contain(QUICLongHeaderPart1)
    ) >> Assign(
        stack.udp.perm.dst_conn_id_len,
        ((quic_header_protocol.header.dst_src_conn_id_len & 0xF0) >> 4) + 3,
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