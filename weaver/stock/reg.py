from weaver.stock import make_reg

runtime = make_reg(0, None, True)
header_parser = make_reg(100, None, True)
instance_table = make_reg(101, None, True)
sequence = make_reg(102, None, True)

# make sure user-defined registers start from 1000
_unused = make_reg(999, None, True)
