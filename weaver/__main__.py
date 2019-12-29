from weaver.misc.code import eth as eth_code, ip as ip_code, next_ip
from weaver.misc.header import eth as eth_action, ip as ip_action
from weaver.code import *
from weaver.writer_context import GlobalContext

b1 = BasicBlock.from_codes(eth_code).optimize()
b2 = BasicBlock.from_codes(ip_code)
context = GlobalContext({next_ip: b2})
context.execute_block_recurse(b2, 0, ip_action)
context.execute_block_recurse(b1, 1, eth_action)
print('/*** Weaver Auto-generated Whitebox Template ***/')
print(context.write_template())
print('/*** Weaver Auto-generated Blackbox Code ***/')
print(context.write_all(b1, 1))
