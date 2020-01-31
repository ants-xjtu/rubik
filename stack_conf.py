from weaver.stock.stacks.gtp import stack, stack_map, stack_entry
from weaver.lang import Event, EqualExpr, ConstRaw, Call, RegProto
from weaver.code import Value
from weaver.auxiliary import RegAux

stack['tcp'].proto.events.event_map['exam'] = Event(
    ConstRaw(Value([], '1')), [
        Call('exam_tcp_content', {
            RegProto(RegAux(1)): stack['tcp'].proto.core.state, 
            RegProto(RegAux(2)): stack['tcp'].proto.core.trans,
            RegProto(RegAux()): stack['tcp'].proto.seq.content(),
        }),
    ]
)
stack['tcp'].proto.events.before_map['exam'] = {'assemble'}