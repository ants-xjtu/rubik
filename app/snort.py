from weaver.lang import layout, Bit, If, Assign, Call
from stock.tcp_ip import stack


class report_status(layout):
    state = Bit(8)
    content = Bit()


stack.tcp.event.report = If(1) >> (
    Assign(report_status.state, stack.tcp.current_state)
    + Assign(report_status.content, stack.tcp.sdu)
    + Call(report_status)
)

# class count_ip(layout):
#     dummy = Bit(8)

# stack.ip.event.report = If(1) >> Call(count_ip)