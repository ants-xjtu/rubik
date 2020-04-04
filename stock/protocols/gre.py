# pylint: disable = unused-wildcard-import
from weaver.lang import *


class GRE_header(layout):
    C = Bit(1)
    R = Bit(1)
    K = Bit(1)
    S = Bit(1)
    strict_source_route = Bit(1)
    recursion_control = Bit(3)
    A = Bit(1)
    reserved = Bit(4)
    version = Bit(3)
    protocol = UInt(16)
    payload_length = UInt(16)
    call_ID = Bit(16)


class GRE_sequence_number(layout):
    sequence_number = UInt(32)


class GRE_ack_number(layout):
    ack_number = UInt(32)


class GRE_perm(layout):
    short_PPP = Bit(8, init=0)
    active_offset = Bit(32, init=0)
    passive_offset = Bit(32, init=0)


class GRE_temp(layout):
    offset = Bit(64)


def gre_parser(ip):
    gre = ConnectionOriented()

    gre.header = GRE_header
    gre.header += If(gre.header.S) >> GRE_sequence_number
    gre.header += If(gre.header.A) >> GRE_ack_number

    gre.selector = ([ip.header.saddr], [ip.header.daddr])

    gre.perm = GRE_perm
    gre.temp = GRE_temp

    gre.prep = (
        If((gre.header.payload_length != 0) & (gre.to_active))
        >> Assign(gre.temp.offset, gre.perm.passive_offset)
        + Assign(
            gre.perm.passive_offset, gre.perm.passive_offset + gre.header.payload_length
        )
    ) + (
        If((gre.header.payload_length != 0) & (gre.to_passive))
        >> Assign(gre.temp.offset, gre.perm.active_offset)
        + Assign(
            gre.perm.active_offset, gre.perm.active_offset + gre.header.payload_length
        )
    )

    gre.seq = Sequence(meta=gre.temp.offset, data=gre.payload, data_len=gre.payload_len)

    dump = PSMState(start=True)
    nothing = PSMState(accept=True)
    gre.psm = PSM(dump, nothing)
    gre.psm.tunneling = (dump >> dump) + Predicate(gre.header.payload_length != 0)
    gre.psm.only_ack = (dump >> dump) + Predicate(gre.header.payload_length == 0)

    gre.event.asm = If(gre.psm.tunneling) >> Assemble()

    return gre
