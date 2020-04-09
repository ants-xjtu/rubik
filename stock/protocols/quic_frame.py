from weaver.lang import *

class QUICFrame(layout):
    frame_type = Bit(8)


class QUICStreamFrameStreamID(layout):
    stream_id = Bit(8)


class QUICStreamFrameStreamIDTail(layout):
    stream_id_tail = Bit(
        ((Const(1) << ((QUICStreamFrameStreamID.stream_id & 0xC0) >> 6)) - 1) << 3
    )


class QUICStreamFrameOffset(layout):
    frame_offset = Bit(8)


class QUICStreamFrameOffsetTail(layout):
    frame_offset_tail = Bit(
        ((Const(1) << ((QUICStreamFrameOffset.frame_offset & 0xC0) >> 6)) - 1) << 3
    )


class QUICStreamFrameLength(layout):
    frame_length = Bit(8)


class QUICStreamFrameLengthTail(layout):
    frame_length_tail = Bit(
        ((Const(1) << ((QUICStreamFrameLength.frame_length & 0xC0) >> 6)) - 1) << 3
    )


class QUICConnectionClose(layout):
    error_code = Bit(16)
    reason_phrase_length = Bit(8)
    reason_phrase = Bit(reason_phrase_length << 3)


class QUICACK(layout):
    last_ack_upper = Bit(2)
    last_ack_lower = Bit(6)
    last_ack_extra = Bit(((Const(1) << last_ack_upper) - 1) << 3)
    ack_delay_upper = Bit(2)
    ack_delay_lower = Bit(6)
    ack_delay_extra = Bit(((Const(1) << ack_delay_upper) - 1) << 3)
    ack_block_count_upper = Bit(2)
    ack_block_count_lower = Bit(6)
    ack_block_count_extra = Bit(((Const(1) << ack_block_count_upper) - 1) << 3)
    ack_block_upper = Bit(2)
    ack_block_lower = Bit(6)
    ack_block_extra = Bit(((Const(1) << ack_block_upper) - 1) << 3)


class QUICMaxStreamData(layout):
    max_data_stream_id_upper = Bit(2)
    max_data_stream_id_lower = Bit(6)
    max_data_stream_id_extra = Bit(((Const(1) << max_data_stream_id_upper) - 1) << 3)
    max_stream_data_upper = Bit(2)
    max_stream_data_lower = Bit(6)
    max_stream_data_extra = Bit(((Const(1) << max_stream_data_upper) - 1) << 3)


class QUICMaxData(layout):
    maximum_data = Bit(8)
    maximum_date_lower = Bit(((Const(1) << ((maximum_data & 0xC0) >> 6)) - 1) << 3)


class QUICMaxStreamID(layout):
    max_stream_id = Bit(16)


class QUICPathChallenge(layout):
    path_challenge = Bit(64)


class QUICPathResponse(layout):
    path_response = Bit(64)


class QUICStopsending(layout):
    stop_stream_id = Bit(8)
    stop_stream_id_tail = Bit(((Const(1) << ((stop_stream_id & 0xC0) >> 6)) - 1) << 3)
    application_error = Bit(16)


class QUICRSTStream(layout):
    rst_var_1 = Bit(8)
    rst_var_2 = Bit(((Const(1) << ((rst_var_1 & 0xC0) >> 6)) - 1) << 3)
    rst_err_code = Bit(16)
    rst_var_3 = Bit(8)
    rst_var_4 = Bit(((Const(1) << ((rst_var_3 & 0xC0) >> 6)) - 1) << 3)


class blank(layout):
    pass

class QUICFrameTempData(layout):
    length = Bit(64)
    offset = Bit(64)
    payload_len = Bit(64)
    real_payload_len = Bit(64)
    data = Bit()

def quic_frame_protocol_parser(stack):
    quic_frame_protocol = Connectionless()
    quic_frame_protocol.header = QUICFrame


    quic_frame_protocol.header += (
        blank
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 1)
            )
            >> QUICRSTStream
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 2)
            )
            >> QUICConnectionClose
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 6)
            )
            >> QUICMaxStreamID
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 0x0C)
            )
            >> QUICStopsending
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 0x0F)
            )
            >> QUICPathResponse
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 0x0E)
            )
            >> QUICPathChallenge
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 0x0D)
            )
            >> QUICACK
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 0x04)
            )
            >> QUICMaxData
        )
        + (
            If(
                (quic_frame_protocol.header.frame_type & 0xF0 == 0)
                & (quic_frame_protocol.header.frame_type == 0x05)
            )
            >> QUICMaxStreamData
        )
        + (
            If(quic_frame_protocol.header.frame_type & 0xF8 == 0x10)
            >> QUICStreamFrameStreamID
            + (
                If(QUICStreamFrameStreamID.stream_id & 0xC0 != 0)
                >> QUICStreamFrameStreamIDTail
            )
            + (
                If(quic_frame_protocol.header.frame_type & 0x04 != 0)
                >> QUICStreamFrameOffset
                + (
                    If(QUICStreamFrameOffset.frame_offset & 0xC0 != 0)
                    >> QUICStreamFrameOffsetTail
                )
            )
            + (
                If(quic_frame_protocol.header.frame_type & 0x02 != 0)
                >> QUICStreamFrameLength
                + (
                    If(QUICStreamFrameLength.frame_length & 0xC0 != 0)
                    >> QUICStreamFrameLengthTail
                )
            )
        )
    )




    def assign_variable_length_int(dst, head, tail):
        return (
            Assign(dst, head & 0b00111111)
            + (If(head & 0b11000000) >> Assign(dst, (dst << 8) + tail[0]))
            + (
                If(head & 0b10000000)
                >> (
                    Assign(dst, (dst << 8) + tail[1])
                    + Assign(dst, (dst << 8) + tail[2])
                    + (
                        If(head & 0b01000000)
                        >> (
                            Assign(dst, (dst << 8) + tail[3])
                            + Assign(dst, (dst << 8) + tail[4])
                            + Assign(dst, (dst << 8) + tail[5])
                            + Assign(dst, (dst << 8) + tail[6])
                        )
                    )
                )
            )
        )


    quic_frame_protocol.temp = QUICFrameTempData
    quic_frame_protocol.prep = (
        If(quic_frame_protocol.header.frame_type & 0xF0 != 0) >> (
            (
                If(quic_frame_protocol.header.frame_type & 0x04 == 0)
                >> Assign(quic_frame_protocol.temp.offset, 0)
                >> Else()
                >> AssignQUICUInt(
                    quic_frame_protocol.temp.offset,
                    quic_frame_protocol.header.frame_offset,
                    quic_frame_protocol.header.frame_offset_tail,
                )
            )
            + (
                If(quic_frame_protocol.header.frame_type & 0x02 != 0)
                >> (
                    AssignQUICUInt(
                        quic_frame_protocol.temp.payload_len,
                        quic_frame_protocol.header.frame_length,
                        quic_frame_protocol.header.frame_length_tail,
                    ) + 
                    Assign(
                        quic_frame_protocol.temp.length, quic_frame_protocol.temp.payload_len
                    )
                ) >> 
                Else() >> Assign(quic_frame_protocol.temp.length, 0)
            )
        ) >> Else() >> (
            (
                If(
                    (quic_frame_protocol.header.frame_type == 0x0D)
                    | (quic_frame_protocol.header.frame_type == 0x0F)
                    | (quic_frame_protocol.header.frame_type == 0x0E)
                    | (quic_frame_protocol.header.frame_type == 0x07)
                    | (quic_frame_protocol.header.frame_type == 0x0C)
                    | (quic_frame_protocol.header.frame_type == 0x04)
                    | (quic_frame_protocol.header.frame_type == 0x06)
                    | (quic_frame_protocol.header.frame_type == 0x05)
                    | (quic_frame_protocol.header.frame_type == 0x02)
                )
                >> Assign(quic_frame_protocol.temp.length, 0)
            )
            + (
                If(quic_frame_protocol.header.frame_type == 0x00)
                >> Assign(quic_frame_protocol.temp.length, quic_frame_protocol.payload_len)
            )
        )
    ) + (
        If(quic_frame_protocol.header_contain(QUICStreamFrameStreamID) == 0)
        >> Assign(quic_frame_protocol.temp.offset, 0)
        + Assign(quic_frame_protocol.temp.data, NoData())
        + Assign(quic_frame_protocol.temp.payload_len, 0)
        >> Else()
        >> Assign(quic_frame_protocol.temp.data, quic_frame_protocol.payload)
    ) + Assign(quic_frame_protocol.temp.real_payload_len, quic_frame_protocol.payload_len)

    quic_frame_protocol.selector = \
        [
            stack.ip.header.saddr,
            stack.udp.header.src_port,
            stack.ip.header.daddr,
            stack.udp.header.dst_port,
            quic_frame_protocol.header.stream_id,
            SliceBeforeOp(quic_frame_protocol.header.stream_id_tail, Const(7))
        ]

    # TODO: states for all data has passed middlebox

    quic_frame_protocol.seq = Sequence(
        meta=quic_frame_protocol.temp.offset,
        data=SliceBeforeOp(quic_frame_protocol.temp.data, quic_frame_protocol.temp.payload_len),
    )

    dump = PSMState(start=True, accept=True)
    frag = PSMState()

    quic_frame_protocol.psm = PSM(dump, frag)

    quic_frame_protocol.psm.other_frame = (dump >> dump) + Predicate(
        quic_frame_protocol.header_contain(QUICStreamFrameStreamID) == 0
    )

    quic_frame_protocol.psm.frag_other_frame = (frag >> frag) + Predicate(
        quic_frame_protocol.header_contain(QUICStreamFrameStreamID) == 0
    )

    quic_frame_protocol.psm.more_frag = (dump >> frag) + Predicate(
        quic_frame_protocol.header_contain(QUICStreamFrameStreamID)
        & (quic_frame_protocol.header.frame_type & 0x01 == 0)
    )

    quic_frame_protocol.psm.more_normal_frag = (frag >> frag) + Predicate(
        quic_frame_protocol.header_contain(QUICStreamFrameStreamID)
        & (quic_frame_protocol.header.frame_type & 0x01 == 0)
    )

    quic_frame_protocol.psm.receiving_all = (frag >> dump) + Predicate(
        quic_frame_protocol.header_contain(QUICStreamFrameStreamID)
        & (quic_frame_protocol.v.header.frame_type & 0x01 != 0)
    )

    quic_frame_protocol.event.asm = (
        If(
            quic_frame_protocol.psm.receiving_all
            | quic_frame_protocol.psm.more_frag
            | quic_frame_protocol.psm.more_normal_frag
        )
        >> Assemble()
    )

    quic_frame_protocol.event.sdu = If(1) >> (
        AssignSDU(quic_frame_protocol.payload[quic_frame_protocol.temp.length:])
    )

    quic_frame_protocol.event += quic_frame_protocol.event.asm, quic_frame_protocol.event.sdu
    return quic_frame_protocol