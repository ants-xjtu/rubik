from weaver.header import Struct, LocateStruct
from weaver.auxiliary import StructRegAux, reg_aux
from weaver.code import Reg


def make_reg(reg_id: Reg, byte_len: int, bit_len: int = None) -> Reg:
    reg_aux[reg_id] = StructRegAux(byte_len, bit_len)
    return reg_id


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
eth = [
    LocateStruct(eth_header),
]
