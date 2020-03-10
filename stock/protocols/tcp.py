from weaver.lang import (
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
)


class tcp_hdr(layout):
    sport = UInt(16)
    dport = UInt(16)
    seq_num = UInt(32)
    ack_num = UInt(32)
    hdr_len = Bit(4)
    blank = Bit(4)
    cwr = Bit(1)
    ece = Bit(1)
    urg = Bit(1)
    ack = Bit(1)
    psh = Bit(1)
    rst = Bit(1)
    syn = Bit(1)
    fin = Bit(1)
    window_size = UInt(16)
    checksum = Bit(16)
    urgent_pointer = Bit(16)


class tcp_eol(layout):
    eol_type = Bit(8, const=0)


class tcp_nop(layout):
    nop_type = Bit(8, const=1)


class tcp_mss(layout):
    mss_type = Bit(8, const=2)
    mss_len = Bit(8)
    mss_value = Bit(16)


class tcp_ws(layout):
    ws_type = Bit(8, const=3)
    ws_len = Bit(8)
    ws_value = Bit(8)


class tcp_SACK_permitted(layout):
    SCAK_permitted_type = Bit(8, const=4)
    SCAK_permitted_len = Bit(8)


class tcp_SACK(layout):
    SACK_type = Bit(8, const=5)
    SACK_len = Bit(8)
    SACK_value = Bit((SACK_len - 2) << 3)


class tcp_TS(layout):
    TS_type = Bit(8, const=8)
    TS_len = Bit(8)
    TS_value = Bit(32)
    TS_echo_reply = Bit(32)


class tcp_cc_new(layout):
    cc_new_type = Bit(8, const=12)
    cc_new_len = Bit(8)
    cc_new_value = Bit(32)


class tcp_blank(layout):
    blank_type = Bit(8)
    blank_len = Bit(8)
    blank_value = Bit((blank_len - 2) << 3)


class tcp_data(layout):
    active_lwnd = Bit(32, init=0)
    passive_lwnd = Bit(32, init=0)
    active_wscale = Bit(32, init=0)
    passive_wscale = Bit(32, init=0)
    active_wsize = Bit(32, init=(1 << 32) - 1)
    passive_wsize = Bit(32, init=(1 << 32) - 1)
    fin_seq1 = Bit(32, init=0)
    fin_seq2 = Bit(32, init=0)


class tcp_temp(layout):
    wnd = Bit(32)
    wnd_size = Bit(32)
    data_len = Bit(32)


def tcp_parser(ip):
    tcp = ConnectionOriented()

    tcp.header = tcp_hdr
    tcp.header += If(tcp.cursor < tcp.header.hdr_len << 2) >> AnyUntil(
        [
            tcp_eol,
            tcp_nop,
            tcp_mss,
            tcp_ws,
            tcp_SACK_permitted,
            tcp_SACK,
            tcp_TS,
            tcp_cc_new,
            tcp_blank,
        ],
        (tcp.cursor < tcp.header.hdr_len << 2) & (tcp.payload_len != 0),
    )

    tcp.selector = (
        [ip.header.saddr, tcp.header.sport],
        [ip.header.daddr, tcp.header.dport],
    )

    tcp.perm = tcp_data
    tcp.temp = tcp_temp

    CLOSED = PSMState(start=True)
    SYN_SENT, SYN_RCV, EST, FIN_WAIT_1, CLOSE_WAIT, LAST_ACK = make_psm_state(6)
    TERMINATE = PSMState(accept=True)

    tcp.prep = If(tcp.header.ack == 1) >> Assign(tcp.temp.data_len, tcp.payload_len)
    tcp.prep = (
        If(tcp.header.syn == 1) >> Assign(tcp.temp.data_len, 1) >> Else() >> tcp.prep
    )
    tcp.prep = (
        If(tcp.header.fin == 1)
        >> Assign(tcp.temp.data_len, tcp.payload_len + 1)
        + (
            If(tcp.current_state == EST)
            >> Assign(tcp.perm.fin_seq1, tcp.header.seq_num + tcp.payload_len)
            >> Else()
            >> Assign(tcp.perm.fin_seq2, tcp.header.seq_num)
        )
        >> Else()
        >> tcp.prep
    )

    def update_wnd(oppo_lwnd, oppo_wscale, oppo_wsize, cur_lwnd, cur_wscale, cur_wsize):
        x = If(tcp.header_contain(tcp_ws)) >> Assign(oppo_wscale, tcp.header.ws_value)
        x += Assign(oppo_wsize, tcp.header.window_size)
        x += Assign(oppo_lwnd, tcp.header.ack_num)
        x += Assign(tcp.temp.wnd, cur_lwnd)
        x += Assign(tcp.temp.wnd_size, cur_wsize << cur_wscale)
        return x

    tcp.prep += If(tcp.to_active == 1) >> update_wnd(
        tcp.perm.passive_lwnd,
        tcp.perm.passive_wscale,
        tcp.perm.passive_wsize,
        tcp.perm.active_lwnd,
        tcp.perm.active_wscale,
        tcp.perm.active_wsize,
    )
    tcp.prep += If(tcp.to_passive == 1) >> update_wnd(
        tcp.perm.active_lwnd,
        tcp.perm.active_wscale,
        tcp.perm.active_wsize,
        tcp.perm.passive_lwnd,
        tcp.perm.passive_wscale,
        tcp.perm.passive_wsize,
    )

    tcp.seq = Sequence(
        meta=tcp.header.seq_num,
        zero_based=False,
        data=tcp.payload,
        data_len=tcp.temp.data_len,
        window=(tcp.temp.wnd, tcp.temp.wnd + tcp.temp.wnd_size),
    )

    tcp.psm = PSM(
        CLOSED, SYN_SENT, SYN_RCV, EST, FIN_WAIT_1, CLOSE_WAIT, LAST_ACK, TERMINATE
    )

    tcp.psm.fake = (CLOSED >> TERMINATE) + Pred(tcp.header.syn == 0)
    tcp.psm.hs1 = (CLOSED >> SYN_SENT) + Pred(
        (tcp.header.syn == 1) & (tcp.header.ack == 0)
    )
    tcp.psm.hs2 = (SYN_SENT >> SYN_RCV) + Pred(
        (tcp.to_active == 1) & (tcp.header.syn == 1) & (tcp.header.ack == 1)
    )
    tcp.psm.hs3 = (SYN_RCV >> EST) + Pred(tcp.v.header.ack == 1)

    tcp.psm.buffering = (EST >> EST) + Pred(tcp.header.fin == 0)

    tcp.psm.wv1 = (EST >> FIN_WAIT_1) + Pred(tcp.v.header.fin == 1)
    tcp.psm.wv2 = (FIN_WAIT_1 >> CLOSE_WAIT) + Pred(
        (tcp.v.header.ack == 1)
        & (tcp.v.header.fin == 0)
        & (tcp.perm.fin_seq1 + 1 == tcp.v.header.ack_num)
    )
    tcp.psm.wv2_fast = (FIN_WAIT_1 >> LAST_ACK) + Pred(
        (tcp.v.header.ack == 1)
        & (tcp.v.header.fin == 1)
        & (tcp.perm.fin_seq1 + 1 == tcp.v.header.ack_num)
    )
    tcp.psm.wv3 = (CLOSE_WAIT >> LAST_ACK) + Pred(tcp.v.header.fin == 1)
    tcp.psm.wv4 = (LAST_ACK >> TERMINATE) + Pred(
        (tcp.v.header.ack == 1) & (tcp.perm.fin_seq2 + 1 == tcp.v.header.ack_num)
    )

    for i, state in enumerate(tcp.psm.states()):
        setattr(tcp.psm, f"rst{i}", (state >> TERMINATE) + Pred(tcp.header.rst == 1))

    tcp.event.asm = If(tcp.psm.buffering) >> Assemble()
    return tcp
