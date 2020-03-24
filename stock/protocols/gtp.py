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
    optional = Bit(
        (((E == 1) | (S == 1) | (PN == 1)) << 1) + ((E == 1) | (S == 1) | (PN == 1))
    )


class gtp_extension_header(layout):
    next_type = Bit(8)
    extension_length = Bit(8)
    extension_data = Bit(((extension_length << 2) - 2) << 3)


class gtp_blank(layout):
    next_type = Bit(8, const=0)


def gtp_parser():
    gtp = Connectionless()
    gtp.header = gtp_hdr
    gtp.header += If(
        (gtp.header.E == 1) | (gtp.header.S == 1) | (gtp.header.PN == 1)
    ) >> AnyUntil([gtp_extension_header, gtp_blank], gtp.header_contain(gtp_blank))
    return gtp
