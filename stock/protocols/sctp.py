from rubik.lang import (
    layout,
    Bit,
    UInt,
    ConnectionOriented,
    If,
    Assign,
    AnyUntil,
    PSMState,
    make_psm_state,
    Else,
    Sequence,
    PSM,
    Pred,
    Assemble,
    NoData,
    Const,
)


class sctp_common_hdr(layout):
    sport = UInt(16)
    dport = UInt(16)
    veri_tag = Bit(32)
    chk_sum = Bit(32)


class sctp_data_hdr(layout):
    data_type = Bit(8, const=0)
    reserved = Bit(5)
    U = Bit(1)
    B = Bit(1)
    E = Bit(1)
    length = UInt(16)
    TSN = UInt(32)
    stream_id = Bit(16)
    stream_seq_num = Bit(16)
    payload_id = Bit(32)


class sctp_init_hdr(layout):
    init_type = Bit(8, const=1)
    init_chunk_flags = Bit(8)
    init_chunk_length = UInt(16)
    initiate_tag = Bit(32)
    a_rwnd = Bit(32)
    number_outbound_stream = UInt(16)
    number_inbound_stream = UInt(16)
    initiate_TSN = UInt(32)


class sctp_init_ack_hdr(layout):
    init_ack_type = Bit(8, const=2)
    init_ack_chunk_flags = Bit(8)
    init_ack_chunk_length = UInt(16)
    init_ack_initiate_tag = Bit(32)
    init_ack_a_rwnd = Bit(32)
    init_ack_number_outbound_stream = UInt(16)
    init_ack_number_inbound_stream = UInt(16)
    init_ack_initiate_TSN = UInt(32)


# class sctp_init_ack_hdr(layout):
class sctp_sack_hdr(layout):
    sack_type = Bit(8, const=3)
    sack_chunk_flag = Bit(8)
    sack_chunk_length = UInt(16)
    cumu_TSN_ack = UInt(32)
    a_rwnd = Bit(32)
    number_of_gap = Bit(16)
    number_of_dup = Bit(16)


class sctp_cookie_echo_hdr(layout):
    cookie_echo_type = Bit(8, const=10)
    cookie_echo_chunk_flag = Bit(8)
    cookie_echo_chunk_length = UInt(16)


class sctp_cookie_ack_hdr(layout):
    cookie_ack_chunk_type = Bit(8, const=11)
    cookie_ack_chunk_flag = Bit(8)
    cookie_ack_chunk_length = UInt(16)


class sctp_shutdown_hdr(layout):
    shutdown_chunk_type = Bit(8, const=7)
    shutdown_chunk_flag = Bit(8)
    shutdown_chunk_length = Bit(8)
    shudown_cumu_TSN_ack = Bit(32)


class sctp_shutdown_ack_hdr(layout):
    shutdown_ack_chunk_type = Bit(8, const=8)
    shutdown_ack_chunk_flag = Bit(8)
    shutdown_ack_chunk_length = Bit(8)


class sctp_shutdown_complete_hdr(layout):
    shutdown_complete_chunk_type = Bit(8, const=14)
    shutdown_complete_chunk_flag = Bit(8)
    shutdown_complete_chunk_length = Bit(8)


class sctp_abort_hdr(layout):
    abort_chunk_type = Bit(8, const=6)
    abort_chunk_flag = Bit(8)
    abort_chunk_length = Bit(8)


class sctp_perm(layout):
    active_seq = Bit(32, init=0)
    passive_seq = Bit(32, init=0)


class sctp_temp(layout):
    seq = Bit(32)
    data_len = Bit(16)


def sctp_parser(ip):
    sctp = ConnectionOriented()

    sctp.header = sctp_common_hdr + AnyUntil(
        [
            sctp_data_hdr,
            sctp_init_hdr,
            sctp_init_ack_hdr,
            sctp_sack_hdr,
            sctp_cookie_echo_hdr,
            sctp_cookie_ack_hdr,
            sctp_shutdown_hdr,
            sctp_shutdown_ack_hdr,
            sctp_shutdown_complete_hdr,
            sctp_abort_hdr,
        ],
        Const(0),
    )

    sctp.selector = (
        [ip.header.saddr, sctp.header.sport],
        [ip.header.daddr, sctp.header.dport],
    )

    sctp.temp = sctp_temp
    sctp.perm = sctp_perm

    CLOSED = PSMState(start=True)
    (
        INIT_SENT,
        INIT_ACK_SENT,
        COOKIE_ECHO_SENT,
        ESTABLISHED,
        MORE_FRAG,
        SHUTDOWN_SENT,
        SHUTDOWN_ACK_SENT,
    ) = make_psm_state(7)
    TERMINATE = PSMState(accept=True)

    sctp.prep = (
        (
            If(sctp.header_contain(sctp_data_hdr))
            >> (
                If(sctp.to_active)
                >> (
                    Assign(
                        sctp.perm.passive_seq, sctp.header.TSN + sctp.header.length - 16
                    )
                    + Assign(sctp.temp.seq, sctp.header.TSN)
                    + Assign(sctp.temp.data_len, sctp.header.length - 16)
                )
                >> Else()
                >> (
                    Assign(
                        sctp.perm.active_seq, sctp.header.TSN + sctp.header.length - 16
                    )
                    + Assign(sctp.temp.seq, sctp.header.TSN)
                    + Assign(sctp.temp.data_len, sctp.header.length - 16)
                )
            )
        )
        + (
            If(sctp.header_contain(sctp_init_hdr))
            >> Assign(sctp.perm.active_seq, sctp.header.initiate_TSN)
        )
        + (
            If(sctp.header_contain(sctp_init_ack_hdr))
            >> Assign(sctp.perm.passive_seq, sctp.header.init_ack_initiate_TSN)
        )
        + (
            If(
                sctp.header_contain(sctp_cookie_echo_hdr)
                | sctp.header_contain(sctp_cookie_ack_hdr)
                | sctp.header_contain(sctp_init_hdr)
                | sctp.header_contain(sctp_init_ack_hdr)
                | sctp.header_contain(sctp_sack_hdr)
            )
            >> (
                Assign(sctp.temp.data_len, 0)
                + (
                    (If(sctp.to_active) >> Assign(sctp.temp.seq, sctp.perm.passive_seq))
                    + (
                        If(sctp.to_passive)
                        >> Assign(sctp.temp.seq, sctp.perm.active_seq)
                    )
                )
            )
        )
    )

    sctp.seq = Sequence(
        meta=sctp.temp.seq,
        zero_based=False,
        data=sctp.payload[: sctp.temp.data_len],
        data_len=sctp.temp.data_len,
        window=None,
    )

    sctp.psm = PSM(
        CLOSED,
        INIT_SENT,
        INIT_ACK_SENT,
        COOKIE_ECHO_SENT,
        ESTABLISHED,
        MORE_FRAG,
        SHUTDOWN_SENT,
        SHUTDOWN_ACK_SENT,
        TERMINATE,
    )

    sctp.psm.hs1 = (CLOSED >> INIT_SENT) + Pred(sctp.header_contain(sctp_init_hdr))
    sctp.psm.hs2 = (INIT_SENT >> INIT_ACK_SENT) + Pred(
        sctp.header_contain(sctp_init_ack_hdr)
    )
    sctp.psm.hs3 = (INIT_ACK_SENT >> COOKIE_ECHO_SENT) + Pred(
        sctp.header_contain(sctp_cookie_echo_hdr)
    )
    sctp.psm.hs4 = (COOKIE_ECHO_SENT >> ESTABLISHED) + Pred(
        sctp.header_contain(sctp_cookie_ack_hdr)
    )

    sctp.psm.sack = (ESTABLISHED >> ESTABLISHED) + Pred(
        sctp.header_contain(sctp_sack_hdr)
    )
    sctp.psm.data_start = (ESTABLISHED >> MORE_FRAG) + Pred(
        sctp.header_contain(sctp_data_hdr)
        & (sctp.header.U == 0)
        & (sctp.header.B == 1)
        & (sctp.header.E == 0)
    )

    sctp.psm.more_data = (MORE_FRAG >> MORE_FRAG) + Pred(
        sctp.header_contain(sctp_data_hdr)
        & (sctp.header.U == 0)
        & (sctp.header.B == 0)
        & (sctp.header.E == 0)
    )

    sctp.psm.data_end = (MORE_FRAG >> ESTABLISHED) + Pred(
        sctp.header_contain(sctp_data_hdr)
        & (sctp.header.U == 0)
        & (sctp.header.B == 0)
        & (sctp.header.E == 1)
    )

    sctp.psm.single_frag = (ESTABLISHED >> ESTABLISHED) + Pred(
        sctp.header_contain(sctp_data_hdr)
        & (sctp.header.U == 0)
        & (sctp.header.B == 1)
        & (sctp.header.E == 1)
    )

    sctp.psm.unordered = (ESTABLISHED >> ESTABLISHED) + Pred(
        sctp.header_contain(sctp_data_hdr) & (sctp.header.U == 1)
    )

    sctp.psm.abort1 = (ESTABLISHED >> TERMINATE) + Pred(
        sctp.header_contain(sctp_abort_hdr)
    )

    sctp.psm.abort2 = (CLOSED >> TERMINATE) + Pred(sctp.header_contain(sctp_abort_hdr))

    sctp.psm.wv1 = (ESTABLISHED >> SHUTDOWN_SENT) + Pred(
        sctp.header_contain(sctp_shutdown_hdr)
    )

    sctp.psm.wv2 = (SHUTDOWN_SENT >> SHUTDOWN_ACK_SENT) + Pred(
        sctp.header_contain(sctp_shutdown_ack_hdr)
    )

    sctp.psm.wv3 = (SHUTDOWN_ACK_SENT >> TERMINATE) + Pred(
        sctp.header_contain(sctp_shutdown_complete_hdr)
    )

    sctp.event.asm = (
        If(sctp.psm.unordered | sctp.psm.single_frag | sctp.psm.data_end) >> Assemble()
    )
    return sctp
