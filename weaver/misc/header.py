from weaver.header import Struct, LocateStruct
from weaver.auxiliary import StructRegAux, reg_aux
from weaver.code import Reg


def make_reg(reg_id: Reg, bit_len: int) -> Reg:
    reg_aux[reg_id] = StructRegAux(bit_len)
    return reg_id


eth_dst = 10000
eth_src = 10001
eth_type = 10002
eth_header = Struct([
    make_reg(eth_dst, 48),
    make_reg(eth_src, 48),
    make_reg(eth_type, 16),
])
eth = [
    LocateStruct(eth_header),
]
