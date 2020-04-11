from weaver.lang import layout, Bit, Connectionless, If, AnyUntil


class gtp_hdr(layout):
    version = Bit(3)
    PT = Bit(1)
    Reserved = Bit(1)
    E = Bit(1)
    S = Bit(1)
    PN = Bit(1)
    MT = Bit(8)
    Total_length = Bit(16)
    TEID = Bit(32)


class var_header(layout):
    seq_no_upper = Bit(16)
    npdu_no = Bit(8)
    next_header_type = Bit(8)


class gtp_extension_header(layout):
    extension_length = Bit(8)
    extension_data = Bit(((extension_length << 2) - 2) << 3)
    next_type = Bit(8)


def gtp_parser():
    gtp = Connectionless()
    gtp.header = gtp_hdr
    gtp.header += (
        If((gtp.header.E == 1) | (gtp.header.S == 1) | (gtp.header.PN == 1))
        >> var_header
    )
    gtp.header += If(gtp.header.E == 1) >> AnyUntil(
        [gtp_extension_header],
        (gtp_extension_header.next_type != 0) & (gtp.payload_len != 0),
    )
    return gtp
