def make_block(text: str) -> str:
    if text:
        text = ('\n' + text).replace('\n', '\n  ') + '\n'
    return '{' + text + '}'


def make_reg(reg_id: int, byte_len: int = None, abstract: bool = False):
    from weaver.auxiliary import reg_aux, RegAux

    reg_aux[reg_id] = RegAux(byte_len, abstract)
    return reg_id
