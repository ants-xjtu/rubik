from weaver.lang import layout, Bit, Connectionless


class udp_hdr(layout):
    src_port = Bit(16)
    dst_port = Bit(16)
    pkt_length = Bit(16)
    checksum = Bit(16)


def udp_parser():
    udp = Connectionless()
    udp.header = udp_hdr
    return udp
