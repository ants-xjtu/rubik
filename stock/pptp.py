# pylint: disable = unused-wildcard-import
from weaver.lang import *

from stock.protocols.eth import eth_parser
from stock.protocols.tcp import tcp_parser
from stock.protocols.ip import ip_parser
from stock.protocols.udp import udp_parser
from stock.protocols.gre import gre_parser
from stock.protocols.ppp import ppp_parser
from stock.protocols.pptp import pptp_parser
from stock.protocols.tcp import tcp_parser


stack = Stack()
stack.eth = eth_parser()
stack.ip1 = ip_parser()
stack.tcp_ctl = tcp_parser(stack.ip1)
stack.pptp = pptp_parser(stack.ip1)
stack.gre = gre_parser(stack.ip1)
stack.ppp = ppp_parser(stack.ip1, stack.gre)
stack.ip2 = ip_parser()
stack.udp = udp_parser()
stack.tcp = tcp_parser(stack.ip2)

stack += (stack.eth >> stack.ip1) + Predicate(1)
stack += (stack.ip1 >> stack.tcp_ctl) + Predicate(
    (stack.ip1.psm.dump | stack.ip1.psm.last) & (stack.ip1.header.protocol == 6)
)
stack += (stack.tcp_ctl >> stack.pptp) + Predicate(
    stack.tcp_ctl.psm.buffering & (stack.tcp_ctl.sdu.length != 0)
)
stack += (stack.ip1 >> stack.gre) + Predicate(
    (stack.ip1.psm.last | stack.ip1.psm.dump) & (stack.ip1.header.protocol == 47)
)
stack += (stack.gre >> stack.ppp) + Predicate(
    (stack.gre.header.protocol == 0x0B88) & stack.gre.psm.tunneling
)
stack += (stack.ppp >> stack.ip2) + Predicate(
    (stack.ppp.temp.protocol == 0x0021) & stack.ppp.psm.tunneling
)
stack += (stack.ip2 >> stack.tcp) + Predicate(stack.ip2.header.protocol == 6)
stack += (stack.ip2 >> stack.udp) + Predicate(stack.ip2.header.protocol == 17)
