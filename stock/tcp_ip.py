from weaver.lang import Stack, Predicate
from stock.protocols import ip_parser, tcp_parser


stack = Stack()
stack.ip = ip_parser()
stack.tcp = tcp_parser(stack.ip)
stack += (stack.ip >> stack.tcp) + Predicate(stack.ip.header.protocol == 6)
