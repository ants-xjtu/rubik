from weaver.lang import layout, Bit, Connectionless

class loopback_hdr(layout):
    family = Bit(32)

def loopback_parser():
    loopback = Connectionless()
    loopback.header = loopback_hdr
    return loopback
