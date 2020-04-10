# pylint: disable = unused-wildcard-import
from weaver.lang import *

from stock.protocols.loopback import loopback_parser
from stock.protocols.quic_udp import udp_parser
from stock.protocols.ip import ip_parser
from stock.protocols.quic_header import quic_header_protocol_parser
from stock.protocols.quic_frame import quic_frame_protocol_parser

# includes loopback, IP and UDP

stack = Stack()
stack.loopback = loopback_parser()
stack.ip = ip_parser()
stack.udp = udp_parser()
stack.quic_header_protocol = quic_header_protocol_parser(stack)
stack.quic_frame_protocol = quic_frame_protocol_parser(stack)


stack += (stack.loopback >> stack.ip) + Predicate(1)
stack += (stack.ip >> stack.udp) + Predicate(
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 17)
)
stack += (stack.udp >> stack.quic_header_protocol) + Predicate(1)

stack += (stack.quic_header_protocol >> stack.quic_frame_protocol) + Predicate(
    stack.quic_header_protocol.psm.loop
)
stack += (stack.quic_frame_protocol >> stack.quic_frame_protocol) + Predicate(
    stack.quic_frame_protocol.temp.real_payload_len > stack.quic_frame_protocol.temp.length
)
