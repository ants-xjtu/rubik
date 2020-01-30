from weaver.stock.protocols.ip import ip
from weaver.stock.protocols.eth import eth
from weaver.writer_context import GlobalContext
from weaver.lang import EqualExpr, ConstRaw
from weaver.code import Value

stack = {}
stack['eth'] = eth().alloc_bundle()
stack['ip'] = ip().alloc_bundle()

stack_map = {}
stack_map['eth'] = {
    EqualExpr(stack['eth'].proto.setup_auto.get('h_protocol'), ConstRaw(Value([], '0x0800'))): 'ip',
}

stack_entry = 'eth'