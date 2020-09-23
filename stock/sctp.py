from rubik.lang import Stack, Predicate, layout 
from stock.protocols import ip_parser, eth_parser, sctp_parser


stack = Stack()
stack.eth = eth_parser()
stack.ip = ip_parser()
stack.sctp = sctp_parser(stack.ip)

stack += (stack.eth >> stack.ip) + Predicate(1)
stack += (stack.ip >> stack.sctp) + Predicate(
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 132))
