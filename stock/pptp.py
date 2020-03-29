# pylint: disable = unused-wildcard-import
from weaver.lang import *

from stock.protocols.tcp import tcp_parser
from stock.protocols.ip import ip_parser
from stock.protocols.udp import udp_parser
from stock.protocols.gre import gre_parser
from stock.protocols.pure_ip import pure_ip_parser
from stock.protocols.ppp import ppp_parser
from stock.protocols.pptp import pptp_parser
from stock.protocols.tcp import tcp_parser


stack = Stack()
stack.ip = ip_parser()
stack.tcp = tcp_parser(stack.ip)
stack.pptp = pptp_parser(stack.ip)
stack.gre = gre_parser(stack.ip)
stack.ppp = ppp_parser(stack.ip, stack.gre)
stack.pure_ip = pure_ip_parser()
stack.udp = udp_parser()
stack.upper_tcp = tcp_parser(stack.pure_ip)

stack += (stack.ip >> stack.tcp) + Predicate(
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 6)
)

stack += (stack.tcp >> stack.pptp) + Predicate(
    stack.tcp.psm.buffering & (stack.tcp.payload_len > 0)
)

stack += (stack.ip >> stack.gre) + Predicate(
    (stack.ip.psm.last | stack.ip.psm.dump) & (stack.ip.header.protocol == 47)
)

stack += (stack.gre >> stack.ppp) + Predicate(
    (stack.gre.header.protocol == 0x880B) & stack.gre.psm.tunneling
)

stack += (stack.ppp >> stack.pure_ip) + Predicate(
    (stack.ppp.temp.protocol == 0x0021) & stack.ppp.psm.tunneling
)

stack += (stack.pure_ip >> stack.upper_tcp) + Predicate(
    stack.pure_ip.header.protocol == 6
)

stack += (stack.pure_ip >> stack.udp) + Predicate(stack.pure_ip.header.protocol == 17)
