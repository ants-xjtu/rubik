from weaver.lang import Stack, Predicate
from stock.protocols import eth_parser, ip_parser, udp_parser, gtp_parser, tcp_parser


stack = Stack()
stack.eth = eth_parser()
stack.ip1 = ip_parser()
stack.udp = udp_parser()
stack.gtp = gtp_parser()
stack.ip2 = ip_parser()
stack.tcp = tcp_parser(stack.ip2)

stack += (stack.eth >> stack.ip1) + Predicate(1)
stack += (stack.ip1 >> stack.udp) + Predicate(
    (stack.ip1.psm.dump | stack.ip1.psm.last) & (stack.ip1.header.protocol == 17)
)
stack += (stack.udp >> stack.gtp) + Predicate(1)
stack += (stack.gtp >> stack.ip2) + Predicate(stack.gtp.header.MT == 255)
stack += (stack.ip2 >> stack.tcp) + Predicate(
    (stack.ip2.psm.dump | stack.ip2.psm.last) & (stack.ip2.header.protocol == 6)
)
