from weaver.stock.stacks.tcp_ip import stack, stack_map, stack_entry
from weaver.lang import Event, EqualExpr, ConstRaw, Call
from weaver.code import Value


stack['tcp'].proto.events.event_map['exam'] = Event(
    ConstRaw(Value([], '1')), [
        Call('exam_tcp_content', []),
    ]
)
stack['tcp'].proto.events.before_map['exam'] = {'assemble'}