from __future__ import annotations
from typing import List, TYPE_CHECKING
from weaver.header import Struct, LocateStruct
from weaver.auxiliary import StructRegAux, reg_aux
from weaver.code import Reg

if TYPE_CHECKING:
    from weaver.header import ParseAction


def make_reg(reg_id: Reg, byte_len: int, bit_len: int = None) -> Reg:
    reg_aux[reg_id] = StructRegAux(byte_len, bit_len)
    return reg_id


# Ethernet Protocol
eth_dst1 = 10000
eth_dst2 = 10001
eth_dst3 = 10002
eth_src1 = 10003
eth_src2 = 10004
eth_src3 = 10005
eth_type = 10006
eth_header = Struct([
    make_reg(eth_dst1, 2),
    make_reg(eth_dst2, 2),
    make_reg(eth_dst3, 2),
    make_reg(eth_src1, 2),
    make_reg(eth_src2, 2),
    make_reg(eth_src3, 2),
    make_reg(eth_type, 2),
])
eth: List[ParseAction] = [
    LocateStruct(eth_header),
]

# IP Protocol
ip_ihl = 20000
ip_ver = 20001
ip_tos = 20002
ip_len = 20003
ip_id = 20004
ip_offset1 = 20005
ip_more_frag = 20006
ip_dont_frag = 20007
ip_none_flag = 20008
ip_offset2 = 20009
ip_ttl = 20010
ip_protocol = 20011
ip_checksum = 20012
ip_src = 20013
ip_dst = 20014
ip_header = Struct([
    make_reg(ip_ihl, 1, 4),
    make_reg(ip_ver, 1, 4),
    make_reg(ip_tos, 1),
    make_reg(ip_len, 2),
    make_reg(ip_id, 2),
    make_reg(ip_offset1, 1, 5),
    make_reg(ip_more_frag, 1, 1),
    make_reg(ip_dont_frag, 1, 1),
    make_reg(ip_none_flag, 1, 1),
    make_reg(ip_offset2, 1),
    make_reg(ip_ttl, 1),
    make_reg(ip_protocol, 1),
    make_reg(ip_checksum, 2),
    make_reg(ip_src, 4),
    make_reg(ip_dst, 4),
])
ip: List[ParseAction] = [
    LocateStruct(ip_header),
]
ip_key = Struct([
    make_reg(20015, 4),
    make_reg(20016, 4),
])
ip_state = 20017
ip_seen_dont_frag = 20018
ip_data = Struct([
    make_reg(ip_state, 1),
    make_reg(ip_seen_dont_frag, 1),
])