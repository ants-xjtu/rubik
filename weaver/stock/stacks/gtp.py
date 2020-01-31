from weaver.stock.protocols import ip, eth, tcp, udp, gtp
from weaver.writer_context import GlobalContext
from weaver.lang import EqualExpr, ConstRaw, one
from weaver.code import Value

stack = {}
stack['eth'] = eth().alloc_bundle()
stack['ip1'] = ip().alloc_bundle()
stack['udp'] = udp().alloc_bundle()
stack['gtp'] = gtp().alloc_bundle()
stack['ip2'] = ip().alloc_bundle()
stack['tcp'] = tcp(stack['ip2']).alloc_bundle()

stack_map = {}
stack_map['eth'] = {
    EqualExpr(stack['eth'].proto.setup_auto.get('h_protocol'), ConstRaw(Value([], '0x0800'))): 'ip1',
}
stack_map['ip1'] = {
    EqualExpr(stack['ip1'].proto.parser.get('protocol'), ConstRaw(Value([], '17'))): 'udp'
}
stack_map['udp'] = {
    ConstRaw(one): 'gtp'
}
stack_map['gtp'] = {
    EqualExpr(stack['gtp'].proto.parser.get('msgtype'), ConstRaw(Value([], '0xff'))): 'ip2'
}
stack_map['ip2'] = {
    EqualExpr(stack['ip2'].proto.parser.get('protocol'), ConstRaw(Value([], '6'))): 'tcp'
}

stack_entry = 'eth'
