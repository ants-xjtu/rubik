from weaver.misc.code import eth as eth_code
from weaver.misc.header import eth as eth_action
from weaver.code import *
from weaver.writer_context import GlobalContext

b1 = BasicBlock.from_codes(eth_code)
b2 = b1.optimize()
# b3 = BasicBlock.from_codes(ip)
# context = GlobalContext({next_ip: b3})
context = GlobalContext({})
context.execute_block_recurse(b2, 0, eth_action)
# context.execute_block_recurse(b3, 1)
print('/*** Weaver Auto-generated Whitebox Template ***/')
print(context.write_template())
print('/*** Weaver Auto-generated Blackbox Code ***/')
print(context.write_all(b2, 1))
