from weaver.lang import layout, Bit, If, Assign, Call
from stock.tcp_ip import stack


class report_status(layout):
    srcport = Bit(16)
    dstport = Bit(16)
    state = Bit(8)
    content = Bit()


stack.tcp.event.report = If(1) >> (
    (
        If(stack.tcp.to_passive)
        >> (
            Assign(report_status.srcport, stack.tcp.header.sport)
            + Assign(report_status.dstport, stack.tcp.header.dport)
        )
    )
    + (
        If(stack.tcp.to_active)
        >> (
            Assign(report_status.srcport, stack.tcp.header.dport)
            + Assign(report_status.dstport, stack.tcp.header.sport)
        )
    )
    + Assign(report_status.state, stack.tcp.current_state)
    + Assign(report_status.content, stack.tcp.sdu)
    + Call(report_status)
)

# class count_ip(layout):
#     dummy = Bit(8)

# stack.ip.event.report = If(1) >> Call(count_ip)
