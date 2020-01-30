from weaver.stock.stacks.tcp_ip import stack, stack_map, stack_entry
from weaver.lang import Event, EqualExpr, ConstRaw, Call
from weaver.code import Value


stack['ip'].proto.events.event_map['count'] = Event(
    EqualExpr(stack['ip'].proto.parser.get('protocol'), ConstRaw(Value([], '6'))), [
        Call('count_tcp_packet', []),
    ]
)
stack['ip'].proto.events.before_map['count'] = {'assemble'}