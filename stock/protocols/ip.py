from weaver.lang import (
    Connectionless,
    layout,
    Bit,
    UInt,
    Assign,
    Sequence,
    PSM,
    PSMState,
    Pred,
    If,
    Assemble,
)


class ip_hdr(layout):
    version = Bit(4)
    ihl = Bit(4)
    tos = Bit(8)
    tot_len = UInt(16)
    id = Bit(16)
    blank = Bit(1)
    dont_frag = Bit(1)
    more_frag = Bit(1)
    f1 = Bit(5)
    f2 = Bit(8)
    ttl = Bit(8)
    protocol = Bit(8)
    check = Bit(16)
    saddr = Bit(32)
    daddr = Bit(32)


class ip_temp(layout):
    offset = Bit(16)
    length = Bit(16)


def ip_parser():
    ip = Connectionless()

    ip.header = ip_hdr
    ip.selector = [ip.header.saddr, ip.header.daddr]

    ip.temp = ip_temp
    ip.prep = Assign(
        ip.temp.offset, ((ip.header.f1 << 8) + ip.header.f2) << 3
    ) + Assign(ip.temp.length, ip.header.tot_len - (ip.header.ihl << 2))

    ip.seq = Sequence(meta=ip.temp.offset, data=ip.payload[: ip.temp.length])

    DUMP = PSMState(start=True, accept=True)
    FRAG = PSMState()
    ip.psm = PSM(DUMP, FRAG)
    ip.psm.dump = (DUMP >> DUMP) + Pred(
        (ip.header.dont_frag == 1)
        | ((ip.header.more_frag == 0) & (ip.temp.offset == 0))
    )
    ip.psm.frag = (DUMP >> FRAG) + Pred(
        (ip.header.more_frag == 1) | (ip.temp.offset != 0)
    )
    ip.psm.more = (FRAG >> FRAG) + Pred(ip.header.more_frag == 1)
    ip.psm.last = (FRAG >> DUMP) + Pred(ip.v.header.more_frag == 0)

    ip.event.asm = If(ip.psm.dump | ip.psm.last) >> Assemble()

    return ip
