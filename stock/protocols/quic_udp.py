from rubik.lang import layout, Bit, Connectionless, Const, PSMState, PSM, Predicate

class udp_hdr(layout):
    src_port = Bit(16)
    dst_port = Bit(16)
    pkt_length = Bit(16)
    checksum = Bit(16)

class udp_perm(layout):
    dst_conn_id_len = Bit(8, init = Const(0))

def udp_parser():
    udp = Connectionless()
    udp.header = udp_hdr
    udp.perm = udp_perm
    udp.selector = [udp.header.src_port, udp.header.dst_port]
    start = PSMState(start = True)
    nothing = PSMState(accept = True)

    udp.psm = PSM(start, nothing)
    udp.psm.dump = (start >> start) + Predicate(1)


    return udp
