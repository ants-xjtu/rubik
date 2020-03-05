from weaver.lang import Stack, Predicate, layout, Bit, If, Assign, Call
from stock.protocols import ip_parser, tcp_parser


stack = Stack()
stack.ip = ip_parser()
stack.tcp = tcp_parser(stack.ip)
stack += (stack.ip >> stack.tcp) + Predicate(stack.ip.header.protocol == 6)


class report_status(layout):
    state = Bit(8)
    content = Bit()


stack.tcp.event.report = If(1) >> (
    Assign(report_status.state, stack.tcp.current_state)
    + Assign(report_status.content, stack.tcp.sdu)
    + Call(report_status)
)
