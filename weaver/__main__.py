from sys import argv
from importlib import import_module

from weaver.compile import compile5a_layer
from weaver.compile2 import compile7_stack, compile7w_stack


stack = import_module(argv[1]).stack
block_map = {
    layer.layer.context.layer_id: compile5a_layer(layer.layer).optimize()
    for layer in stack.name_map.values()
}
inst_decls = {
    layer.layer.context.layer_id: layer.layer.context.inst.decl(layer.layer.context)
    for layer in stack.name_map.values()
    if layer.layer.context.inst is not None
}

print("/* Weaver Whitebox Code Template */")
print(compile7w_stack(stack.context))
print("/* Weaver Auto-generated Blackbox Code */")
print(
    compile7_stack(
        stack.context,
        block_map,
        inst_decls,
        len(stack.name_map),
        stack.entry.layer.context.layer_id,
    )
)
