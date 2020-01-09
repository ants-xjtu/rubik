from weaver.stock.code import eth as eth_code, ip as ip_code, next_ip
from weaver.stock.header import eth as eth_action, ip as ip_action, ip_data
from weaver.code import BasicBlock
from weaver.writer_context import GlobalContext

b1 = BasicBlock.from_codes(eth_code).optimize()
b2 = BasicBlock.from_codes(ip_code).optimize()
cxt = GlobalContext({next_ip: b2})
cxt.execute_block_recurse(b1, 0, eth_action)
print(cxt.write_all(b1))
