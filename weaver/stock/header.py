from __future__ import annotations
from typing import List, TYPE_CHECKING
from weaver.header import Struct, LocateStruct, ParseByteSlice, TaggedParseLoop
from weaver.auxiliary import StructRegAux, reg_aux, HeaderStructAux, DataStructAuxCreator, RegAux
from weaver.code import Reg, Value, AggValue
from weaver.stock.reg import header_parser
from weaver.writer import TotalLengthWriter, ParsedLengthWriter

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
], HeaderStructAux.create)
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
], HeaderStructAux.create)
ip: List[ParseAction] = [
    LocateStruct(ip_header),
]
ip_state = 20017
ip_expr1 = 20018
ip_data = Struct([
    make_reg(ip_state, 1),
    make_reg(ip_expr1, 1),
], DataStructAuxCreator([
    ip_src,
    ip_dst,
]))

# TCP Protocol
tcp_sport = 30000
tcp_dport = 30001
tcp_seq = 30002
tcp_acknum = 30003
# blank 30004
tcp_hdrlen = 30005
tcp_fin = 30006
tcp_syn = 30007
tcp_rst = 30008
tcp_psh = 30009
tcp_ack = 30010
tcp_urg = 30011
tcp_ece = 30012
tcp_cwr = 30013
tcp_wndsize = 30014
tcp_checksum = 30015
tcp_urgptr = 30016
tcp_header = Struct([
    make_reg(tcp_sport, 2),
    make_reg(tcp_dport, 2),
    make_reg(tcp_seq, 4),
    make_reg(tcp_acknum, 4),
    make_reg(30004, 1, 4),
    make_reg(tcp_hdrlen, 1, 4),
    make_reg(tcp_fin, 1, 1),
    make_reg(tcp_syn, 1, 1),
    make_reg(tcp_rst, 1, 1),
    make_reg(tcp_psh, 1, 1),
    make_reg(tcp_ack, 1, 1),
    make_reg(tcp_urg, 1, 1),
    make_reg(tcp_ece, 1, 1),
    make_reg(tcp_cwr, 1, 1),
    make_reg(tcp_wndsize, 2),
    make_reg(tcp_checksum, 2),
    make_reg(tcp_urgptr, 2),
], HeaderStructAux.create)
tcp_header_type = 30017
reg_aux[tcp_header_type] = RegAux(1)
tcp_header_eol = Struct([], HeaderStructAux.create)
tcp_header_nop = Struct([], HeaderStructAux.create)
tcp_header_mss = Struct([
    make_reg(30018, 1),
    make_reg(30019, 2),
], HeaderStructAux.create)
tcp_ws_value = 30021
tcp_header_ws = Struct([
    make_reg(30020, 1),
    make_reg(tcp_ws_value, 1),
], HeaderStructAux.create)
tcp_header_sackperm = Struct([
    make_reg(30022, 1),
], HeaderStructAux.create)
tcp_header_ts = Struct([
    make_reg(30023, 1),
    make_reg(30024, 4),
    make_reg(30025, 4),
], HeaderStructAux.create)
tcp_header_ccnew = Struct([
    make_reg(30026, 1),
    make_reg(30027, 4),
], HeaderStructAux.create)
tcp_blank_len = 30028
tcp_header_blank = Struct([
    make_reg(tcp_blank_len, 1),
], HeaderStructAux.create)
tcp_blank_value = 30029
reg_aux[tcp_blank_value] = RegAux()
tcp: List[ParseAction] = [
    LocateStruct(tcp_header),
    TaggedParseLoop(AggValue([
        Value([header_parser], 'parser->parsed_length',
              aux=ParsedLengthWriter()),
        Value([tcp_hdrlen], '{0}'),
        Value([header_parser], 'parser->total_length', aux=TotalLengthWriter()),
    ], '{0} < ({1} << 2) && {0} < {2}'), tcp_header_type, {
        0: [LocateStruct(tcp_header_eol)],
        1: [LocateStruct(tcp_header_nop)],
        2: [LocateStruct(tcp_header_mss)],
        3: [LocateStruct(tcp_header_ws)],
        4: [LocateStruct(tcp_header_sackperm)],
        8: [LocateStruct(tcp_header_ts)],
        12: [LocateStruct(tcp_header_ccnew)],
        None: [
            LocateStruct(tcp_header_blank),
            ParseByteSlice(tcp_blank_value, Value([tcp_blank_len], '{0} - 2')),
        ]
    })
]
tcp_data_state = make_reg(40000, 1)
tcp_data_fin_seq_1 = make_reg(40003, 4)
tcp_data_fin_seq_2 = make_reg(40004, 4)
tcp_data_passive_lwnd = make_reg(40005, 4)
tcp_data_passive_wscale = make_reg(40006, 1)
tcp_data_passive_wsize = make_reg(40007, 4)
tcp_data_active_lwnd = make_reg(40008, 4)
tcp_data_active_wscale = make_reg(40009, 1)
tcp_data_active_wsize = make_reg(40010, 4)
tcp_data_seen_ack = make_reg(40011, 1)
tcp_data_seen_fin = make_reg(40012, 1)
tcp_data_wv2_expr = make_reg(40013, 1)
tcp_data_wv2_fast_expr = make_reg(40014, 1)
tcp_data_wv4_expr = make_reg(40015, 1)
tcp_data = Struct([
    tcp_data_state,
    tcp_data_fin_seq_1,
    tcp_data_fin_seq_2,
    tcp_data_passive_lwnd,
    tcp_data_passive_wscale,
    tcp_data_passive_wsize,
    tcp_data_active_lwnd,
    tcp_data_active_wscale,
    tcp_data_active_wsize,
    tcp_data_seen_ack,
    tcp_data_seen_fin,
    tcp_data_wv2_expr,
    tcp_data_wv2_fast_expr,
    tcp_data_wv4_expr,
], DataStructAuxCreator([
    ip_src, tcp_sport,
    ip_dst, tcp_dport,
]))
