# pylint: disable = unused-wildcard-import
from weaver.lang import *


class QUICFrame(layout):
    frame_type = Bit(8)


class StreamID(layout):
    stream_id = Bit(8)


def tail_bit(head):
    return Bit(((Const(1) << ((head & 0xC0) >> 6)) - 1) << 3)


class StreamIDTail(layout):
    stream_id_tail = tail_bit(StreamID.stream_id)


class FrameOffset(layout):
    frame_offset = Bit(8)


class FrameOffsetTail(layout):
    frame_offset_tail = tail_bit(FrameOffset.frame_offset)


class FrameLength(layout):
    frame_length = Bit(8)


class FrameLengthTail(layout):
    frame_length_tail = tail_bit(FrameLength.frame_length)


class ConnectionClose(layout):
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


class MaxStreamData(layout):
    max_data_stream_id_upper = Bit(2)
    max_data_stream_id_lower = Bit(6)
    max_data_stream_id_extra = Bit(((Const(1) << max_data_stream_id_upper) - 1) << 3)
    max_stream_data_upper = Bit(2)
    max_stream_data_lower = Bit(6)
    max_stream_data_extra = Bit(((Const(1) << max_stream_data_upper) - 1) << 3)


class MaxData(layout):
    maximum_data = Bit(8)
    maximum_date_lower = tail_bit(maximum_data)


class MaxStreamID(layout):
    max_stream_id = Bit(16)


class PathChallenge(layout):
    path_challenge = Bit(64)


class PathResponse(layout):
    path_response = Bit(64)


class StopSending(layout):
    stop_stream_id = Bit(8)
    stop_stream_id_tail = tail_bit(stop_stream_id)
    application_error = Bit(16)


class RSTStream(layout):
    rst_var_1 = Bit(8)
    rst_var_2 = tail_bit(rst_var_1)
    rst_err_code = Bit(16)
    rst_var_3 = Bit(8)
    rst_var_4 = tail_bit(rst_var_3)


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
    global_frames = blank
    for frame_type, layout in [
        (0x01, RSTStream),
        (0x02, ConnectionClose),
        (0x06, MaxStreamID),
        (0x0C, StopSending),
        (0x0F, PathResponse),
        (0x0E, PathChallenge),
        (0x0D, QUICACK),
        (0x04, MaxData),
        (0x05, MaxStreamData),
    ]:
        global_frames += If(QUICFrame.frame_type == frame_type) >> layout

    def head_tail(head_layout, head_var, tail_layout):
        return head_layout + (If(head_var & 0xC0 != 0) >> tail_layout)

    frame_type = quic_frame_protocol.header.frame_type
    quic_frame_protocol.header += (
        blank
        + (If(frame_type & 0xF0 == 0) >> global_frames)
        + (
            If(frame_type & 0xF8 == 0x10)
            >> head_tail(StreamID, StreamID.stream_id, StreamIDTail)
            + (
                If(frame_type & 0x04 != 0)
                >> head_tail(FrameOffset, FrameOffset.frame_offset, FrameOffsetTail)
            )
            + (
                If(frame_type & 0x02 != 0)
                >> head_tail(FrameLength, FrameLength.frame_length, FrameLengthTail)
            )
        )
    )

    quic_frame_protocol.temp = QUICFrameTempData
    quic_frame_protocol.prep = (
        (
            If(quic_frame_protocol.header.frame_type & 0xF0 != 0)
            >> (
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
                        )
                        + Assign(
                            quic_frame_protocol.temp.length,
                            quic_frame_protocol.temp.payload_len,
                        )
                    )
                    >> Else()
                    >> Assign(quic_frame_protocol.temp.length, 0)
                )
            )
            >> Else()
            >> (
                If(frame_type == 0)
                >> Assign(
                    quic_frame_protocol.temp.length, quic_frame_protocol.payload_len
                )
                >> Else()
                >> Assign(quic_frame_protocol.temp.length, 0)
            )
        )
        + (
            If(quic_frame_protocol.header_contain(StreamID) == 0)
            >> (
                Assign(quic_frame_protocol.temp.offset, 0)
                + Assign(quic_frame_protocol.temp.data, NoData())
                + Assign(quic_frame_protocol.temp.payload_len, 0)
            )
            >> Else()
            >> Assign(quic_frame_protocol.temp.data, quic_frame_protocol.payload)
        )
        + Assign(
            quic_frame_protocol.temp.real_payload_len, quic_frame_protocol.payload_len
        )
    )

    quic_frame_protocol.selector = [
        stack.ip.header.saddr,
        stack.udp.header.src_port,
        stack.ip.header.daddr,
        stack.udp.header.dst_port,
        quic_frame_protocol.header.stream_id,
        SliceBeforeOp(quic_frame_protocol.header.stream_id_tail, Const(7)),
    ]

    # TODO: states for all data has passed middlebox

    quic_frame_protocol.seq = Sequence(
        meta=quic_frame_protocol.temp.offset,
        data=SliceBeforeOp(
            quic_frame_protocol.temp.data, quic_frame_protocol.temp.payload_len
        ),
    )

    dump = PSMState(start=True, accept=True)
    frag = PSMState()
    quic_frame_protocol.psm = PSM(dump, frag)
    quic_frame_protocol.psm.other_frame = (dump >> dump) + Predicate(
        quic_frame_protocol.header_contain(StreamID) == 0
    )
    quic_frame_protocol.psm.frag_other_frame = (frag >> frag) + Predicate(
        quic_frame_protocol.header_contain(StreamID) == 0
    )
    quic_frame_protocol.psm.more_frag = (dump >> frag) + Predicate(
        quic_frame_protocol.header_contain(StreamID) & (frame_type & 0x01 == 0)
    )
    quic_frame_protocol.psm.more_normal_frag = (frag >> frag) + Predicate(
        quic_frame_protocol.header_contain(StreamID) & (frame_type & 0x01 == 0)
    )
    quic_frame_protocol.psm.receiving_all = (frag >> dump) + Predicate(
        quic_frame_protocol.header_contain(StreamID)
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
        AssignSDU(quic_frame_protocol.payload[quic_frame_protocol.temp.length :])
    )

    quic_frame_protocol.event += (
        quic_frame_protocol.event.asm,
        quic_frame_protocol.event.sdu,
    )
    return quic_frame_protocol
