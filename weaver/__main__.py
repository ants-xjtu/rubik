from weaver.stock.code import eth as eth_code, ip as ip_code, next_ip, tcp as tcp_code, next_tcp
from weaver.stock.header import eth as eth_action, ip as ip_action, ip_data, tcp as tcp_action, tcp_data
from weaver.code import BasicBlock
from weaver.writer_context import GlobalContext

b1 = BasicBlock.from_codes(eth_code).optimize()
b2 = BasicBlock.from_codes(ip_code).optimize()
b3 = BasicBlock.from_codes(tcp_code).optimize()
cxt = GlobalContext({next_ip: b2, next_tcp: b3})
cxt.execute_block_recurse(b1, eth_action)
cxt.execute_block_recurse(b2, ip_action, ip_data)
cxt.execute_block_recurse(b3, tcp_action, tcp_data)
cxt.execute_all()

print('/* Weaver Whitebox Code Template */')
print(cxt.write_template())
print('/* Weaver Auto-generated Blackbox Code */')
print(cxt.write_all(b1))
