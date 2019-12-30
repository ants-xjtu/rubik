from weaver.auxiliary import *


def make_reg(reg_id: 'Reg', byte_len: int = None, abstract: bool = False):
    reg_aux[reg_id] = RegAux(byte_len, abstract)
    return reg_id
