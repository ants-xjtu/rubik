from weaver.stock.code import eth as eth_code, ip as ip_code, next_ip
from weaver.stock.header import eth as eth_action, ip as ip_action, ip_data
from weaver.code import BasicBlock
from weaver.write import write

b1 = BasicBlock.from_codes(eth_code).optimize()
b2 = BasicBlock.from_codes(ip_code).optimize()
for block in b2.recurse():
    print(block)
    print()