from sys import argv
from importlib import import_module

from weaver.compile import compile5a_layer
from weaver.compile2 import compile7_stack, compile7w_stack


stack = import_module(argv[1]).stack
block_map = {layer: compile5a_layer(layer.layer) for layer in stack.name_map.values()}
entry = block_map[stack.entry]
blocks = list(block_map.values())
inst_decls = {
    layer.layer.context.layer_id: layer.layer.context.inst.decl(layer.layer.context)
    for layer in stack.name_map.values()
    if layer.layer.context.inst is not None
}

print("/* Weaver Whitebox Code Template */")
print(compile7w_stack(stack.context))
print("/* Weaver Auto-generated Blackbox Code */")
print(compile7_stack(stack.context, blocks, inst_decls, len(stack.name_map), entry))
