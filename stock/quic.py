from weaver.lang import *

from stock.protocols.loopback import loopback_parser
from stock.protocols.quic_udp import udp_parser
from stock.protocols.ip import ip_parser

# includes loopback, IP and UDP

stack = Stack()
stack.loopback = loopback_parser()
stack.ip = ip_parser()
stack.udp = udp_parser()

stack += (stack.loopback >> stack.ip) + Predicate(1)
stack += (stack.ip >> stack.udp) + Predicate((stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 17))

class QUICHeaderFormPacketType(layout):
    header_form_packet_type = Bit(8)

class QUICLongHeaderPart1(layout):
    version = Bit(32)
    dst_src_conn_id_len = Bit(8)


class QUICLongHeaderOptionalDstConnID(layout):
    dst_conn_id = Bit((((QUICLongHeaderPart1.dst_src_conn_id_len & 0xF0) >> 4) + 3) * 8)


class QUICLongHeaderOptionalSrcConnID(layout):
    src_conn_id = Bit(((QUICLongHeaderPart1.dst_src_conn_id_len & 0x0F) + 3) * 8)


class QUICLongHeaderPart2(layout):
    payload_length_first_byte = Bit(8)


class QUICLongHeaderOptionalPayloadLengthTail(layout):
    payload_length_tail = \
        Bit(((Const(1) << ((QUICLongHeaderPart2.payload_length_first_byte & 0xC0) >> 6)) - 1) * 8)


class QUICLongHeaderPart3(layout):
    packet_number = Bit(32)


class QUICShortHeader(layout):
    dst_conn_id = Bit(stack.layer.udp.perm.dst_conn_id_len * 8)
    # packet_number = \
    #     byte(1 << (QUICHeaderFormPacketType.header_form_packet_type & 0x03))
    packet_number = Bit(8)


quic_header_protocol = ConnectionOriented()
quic_header_protocol.header = \
    QUICHeaderFormPacketType + \
    (If(quic_header_protocol.header.header_form_packet_type & 0x80 != 0) >> \
        QUICLongHeaderPart1 + \
        (If(quic_header_protocol.header.dst_src_conn_id_len & 0xF0 != 0) >> \
            QUICLongHeaderOptionalDstConnID) + \
        (If(quic_header_protocol.header.dst_src_conn_id_len & 0x0F != 0) >> \
            QUICLongHeaderOptionalSrcConnID) + \
        QUICLongHeaderPart2 + \
        (If(quic_header_protocol.header.payload_length_first_byte & 0xC0 != 0) >> \
            QUICLongHeaderOptionalPayloadLengthTail) + \
        QUICLongHeaderPart3) + \
    (If(quic_header_protocol.header.header_form_packet_type & 0x80 == 0) >> \
        QUICShortHeader)
quic_header_protocol.preprocess = \
    If(quic_header_protocol.header_contain(QUICLongHeaderPart1)) >> \
        Assign(stack.layer.udp.perm.dst_conn_id_len, \
            ((quic_header_protocol.header.dst_src_conn_id_len & 0xF0) >> 4) + 3)

# TODO: change to Connection ID
quic_header_protocol.selector = ([stack.layer.ip.header.saddr, stack.layer.udp.header.src_port],
                                [stack.layer.ip.header.daddr, stack.layer.udp.header.dst_port])

# TODO: drive this state machine with `quic_frame`'s packets
start = PSMState(start = True, accept = True)
quic_header_protocol.psm = PSM(start)

quic_header_protocol.psm.loop = \
    (start >> start) + Predicate(1)

stack.quic_header_protocol = quic_header_protocol
stack += (stack.layer.udp >> stack.layer.quic_header_protocol) + Predicate(1)


class QUICFrame(layout):
    frame_type = Bit(8)


class QUICStreamFrameStreamID(layout):
    stream_id = Bit(8)


class QUICStreamFrameStreamIDTail(layout):
    stream_id_tail = \
        Bit(((Const(1) << ((QUICStreamFrameStreamID.stream_id & 0xC0) >> 6)) - 1) * 8)


class QUICStreamFrameOffset(layout):
    frame_offset = Bit(8)


class QUICStreamFrameOffsetTail(layout):
    frame_offset_tail = \
        Bit(((Const(1) << ((QUICStreamFrameOffset.frame_offset & 0xC0) >> 6)) - 1) * 8)


class QUICStreamFrameLength(layout):
    frame_length = Bit(8)


class QUICStreamFrameLengthTail(layout):
    frame_length_tail = \
        Bit(((Const(1) << ((QUICStreamFrameLength.frame_length & 0xC0) >> 6)) - 1) * 8)


class QUICConnectionClose(layout):
    error_code = Bit(16)
    reason_phrase_length = Bit(8)
    reason_phrase = Bit(reason_phrase_length * 8)

class QUICACK(layout):
    last_ack_upper = Bit(2)
    last_ack_lower = Bit(6)
    last_ack_extra = Bit(((Const(1) << last_ack_upper ) - 1) * 8)
    ack_delay_upper = Bit(2)
    ack_delay_lower = Bit(6)
    ack_delay_extra = Bit(((Const(1) << ack_delay_upper ) - 1) * 8)
    ack_block_count_upper = Bit(2)
    ack_block_count_lower = Bit(6)
    ack_block_count_extra = Bit(((Const(1) << ack_block_count_upper ) - 1) * 8)
    ack_block_upper = Bit(2)
    ack_block_lower = Bit(6)
    ack_block_extra = Bit(((Const(1) << ack_block_upper ) - 1) * 8)

class QUICMaxStreamData(layout):
    max_data_stream_id_upper = Bit(2)
    max_data_stream_id_lower = Bit(6)
    max_data_stream_id_extra = Bit(((Const(1) << max_data_stream_id_upper ) - 1) * 8)
    max_stream_data_upper = Bit(2)
    max_stream_data_lower = Bit(6)
    max_stream_data_extra = Bit(((Const(1) << max_stream_data_upper ) - 1) * 8)

class QUICMaxData(layout):
    maximum_data = Bit(8)
    maximum_date_lower = Bit( ((Const(1) << ((maximum_data & 0xC0) >> 6)) - 1) * 8)

class QUICMaxStreamID(layout):
    max_stream_id = Bit(16)


class QUICPathChallenge(layout):
    path_challenge = Bit(64)

class QUICPathResponse(layout):
    path_response = Bit(64)

class QUICStopsending(layout):
    stop_stream_id = Bit(8)
    stop_stream_id_tail = \
        Bit(((Const(1) << ((stop_stream_id & 0xC0) >> 6)) - 1) * 8)
    application_error = Bit(16)

class QUICRSTStream(layout):
    rst_var_1 = Bit(8)
    rst_var_2 = Bit(((Const(1) << ((rst_var_1 & 0xC0) >> 6)) - 1) * 8)
    rst_err_code = Bit(16)
    rst_var_3 = Bit(8)
    rst_var_4 = Bit(((Const(1) << ((rst_var_3 & 0xC0) >> 6)) - 1) * 8)


quic_frame_protocol = Connectionless()
quic_frame_protocol.header = QUICFrame + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 1)) >> \
        QUICRSTStream) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 2)) >> \
        QUICConnectionClose) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 6)) >> \
        QUICMaxStreamID) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 0x0C)) >> \
        QUICStopsending) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 0x0F)) >> \
        QUICPathResponse) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 0x0E)) >> \
        QUICPathChallenge) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 0x0D)) >> \
        QUICACK) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 0x04)) >> \
        QUICMaxData) + \
    (If((quic_frame_protocol.header.frame_type & 0xF0 == 0) & (quic_frame_protocol.header.frame_type == 0x05)) >> \
        QUICMaxStreamData) + \
    (If(quic_frame_protocol.header.frame_type & 0xF8 == 0x10) >> \
        QUICStreamFrameStreamID + \
        (If(quic_frame_protocol.header.stream_id & 0xC0 != 0) >> \
            QUICStreamFrameStreamIDTail) + \
        (If(quic_frame_protocol.header.frame_type & 0x04 != 0) >> \
            QUICStreamFrameOffset + \
            (If(quic_frame_protocol.header.frame_offset & 0xC0 != 0) >> \
                QUICStreamFrameOffsetTail)) + \
        (If(quic_frame_protocol.header.frame_type & 0x02 != 0) >> \
            QUICStreamFrameLength + \
            (If(quic_frame_protocol.header.frame_length & 0xC0 != 0) >> \
                QUICStreamFrameLengthTail)))


class QUICFrameTempData(layout):
    length = Bit(64)
    offset = Bit(64)
    payload_len = Bit(64)
    data = Bit(64)

quic_frame_protocol.temp = QUICFrameTempData
quic_frame_protocol.preprocess = \
    (If(quic_frame_protocol.header.frame_type & 0xF0 != 0) >> \
        (If(quic_frame_protocol.header.frame_type & 0x04 == 0) >> \
            Assign(quic_frame_protocol.temp.offset, 0) >>
        Else() >> 
            Assign(quic_frame_protocol.temp.offset,
                    ((quic_frame_protocol.header.frame_offset & 0x3F) << (((quic_frame_protocol.header.frame_offset & 0xC0) >> 6) * 8)) + 
                    quic_frame_protocol.header.frame_offset_tail * ((quic_frame_protocol.header.frame_offset & 0xC0) >> 6))) + 
        (If(quic_frame_protocol.header.frame_type & 0x02 != 0) >> \
            Assign(quic_frame_protocol.temp.payload_len,
                    ((quic_frame_protocol.header.frame_length & 0x3F) << (((quic_frame_protocol.header.frame_length & 0xC0) >> 6) * 8)) +
                    quic_frame_protocol.header.frame_length_tail * ((quic_frame_protocol.header.frame_length & 0xC0) >> 6)))) + \
    (If(quic_frame_protocol.header_contain(QUICStreamFrameStreamID) == 0) >> 
        Assign(quic_frame_protocol.temp.offset, 0) + 
        Assign(quic_frame_protocol.temp.data, NoData()) + 
        Assign(quic_frame_protocol.temp.payload_len, 0) >> 
    Else() >>
        Assign(quic_frame_protocol.temp.data, quic_frame_protocol.payload)) 

quic_frame_protocol.selector = ([ 
    stack.layer.ip.header.saddr, 
    stack.layer.udp.header.src_port, 
    quic_frame_protocol.header.stream_id, 
    quic_frame_protocol.header.stream_id_tail
],
[ 
    stack.layer.ip.header.daddr, 
    stack.layer.udp.header.dst_port, 
    quic_frame_protocol.header.stream_id, 
    quic_frame_protocol.header.stream_id_tail
])

class QUICFramePermData(layout):
    accept_length = Bit(32, init = 0)
    expect_length = Bit(32)


quic_frame_protocol.perm = QUICFramePermData


# TODO: states for all data has passed middlebox

quic_frame_protocol.seq = Sequence(meta = quic_frame_protocol.temp.offset, data = quic_frame_protocol.temp.data, data_len = quic_frame_protocol.temp.payload_len)

dump = PSMState(start = True, accept = True)
frag = PSMState()

quic_frame_protocol.psm = PSM(dump, frag)

quic_frame_protocol.psm.other_frame = \
    (dump >> dump) + \
    Predicate(quic_frame_protocol.header_contain(QUICStreamFrameStreamID) == 0)

quic_frame_protocol.psm.more_frag = (dump >> frag) + \
    Predicate(quic_frame_protocol.header_contain(QUICStreamFrameStreamID) & (quic_frame_protocol.header.frame_type & 0x01 == 0))

quic_frame_protocol.psm.more_normal_frag = (frag >> frag) + \
    Predicate(quic_frame_protocol.header_contain(QUICStreamFrameStreamID) & (quic_frame_protocol.header.frame_type & 0x01 == 0))

quic_frame_protocol.psm.receiving_all = (frag >> dump) + \
    Predicate(quic_frame_protocol.header_contain(QUICStreamFrameStreamID) & (quic_frame_protocol.v.header.frame_type & 0x01 != 0))

quic_frame_protocol.event.asm = If(quic_frame_protocol.psm.receiving_all | quic_frame_protocol.psm.more_frag | quic_frame_protocol.psm.more_normal_frag) >> Assemble()
quic_frame_protocol.event.length = \
    (If(quic_frame_protocol.header.frame_type & 0xF0 == 0) >> \
        (If((quic_frame_protocol.header.frame_type == 0x0D) | 
            (quic_frame_protocol.header.frame_type == 0x0F) | 
            (quic_frame_protocol.header.frame_type == 0x0E) |
            (quic_frame_protocol.header.frame_type == 0x07) | 
            (quic_frame_protocol.header.frame_type == 0x0C) | 
            (quic_frame_protocol.header.frame_type == 0x04) | 
            (quic_frame_protocol.header.frame_type == 0x06) | 
            (quic_frame_protocol.header.frame_type == 0x05) |
            (quic_frame_protocol.header.frame_type == 0x02)) >> Assign(quic_frame_protocol.temp.length, 0)) + \
        (If(quic_frame_protocol.header.frame_type == 0x00) >> \
            Assign(quic_frame_protocol.temp.length, quic_frame_protocol.payload_len))) + \
    (If(quic_frame_protocol.header.frame_type & 0xF0 != 0) >> \
        (If(quic_frame_protocol.header.frame_type & 0x02 == 0) >> \
            Assign(quic_frame_protocol.temp.length, 0)) + \
        (If(quic_frame_protocol.header.frame_type & 0x02 != 0) >> \
            Assign(quic_frame_protocol.temp.length, quic_frame_protocol.temp.payload_len)))


stack.quic_frame_protocol = quic_frame_protocol
stack += (stack.quic_header_protocol >> stack.quic_frame_protocol) + Predicate(stack.quic_header_protocol.psm.loop)
stack += (stack.quic_frame_protocol >> stack.quic_frame_protocol) + Predicate(stack.quic_frame_protocol.payload_len > stack.quic_frame_protocol.temp.length)

