from rubik.lang import Stack, Predicate, layout, Bit, If, Assign, Call
from stock.protocols import ip_parser, tcp_parser, eth_parser, udp_parser


stack = Stack()
stack.eth = eth_parser()
stack.ip = ip_parser()
stack.tcp = tcp_parser(stack.ip)
stack.udp = udp_parser()

stack += (stack.eth >> stack.ip) + Predicate(1)
stack += (stack.ip >> stack.tcp) + Predicate(
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 6)
)
stack += (stack.ip >> stack.udp) + Predicate(
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 17)
)

# stack.tcp.layer.context.buffer_data = False