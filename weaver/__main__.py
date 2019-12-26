from weaver.misc.code import *
from weaver.code import *
from weaver.writer import write_all

b1 = BasicBlock.from_codes(ip)
b2 = b1.optimize()
text = write_all([b1], b1.block_id)
print(text)