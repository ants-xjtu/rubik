from weaver.lang import layout, Bit, Connectionless


class ethernet_hdr(layout):
    blank1 = Bit(64)
    blank2 = Bit(32)
    blank3 = Bit(16)


def eth_parser():
    eth = Connectionless()
    eth.header = ethernet_hdr
    return eth
