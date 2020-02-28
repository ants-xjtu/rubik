from sys import argv
from importlib import import_module

from weaver.compile import (
    StackContext,
    LayerContext,
    compile0_prototype,
    compile5_layer,
)


protocol = import_module(argv[1]).ip_parser()
stack_context = StackContext()
layer_context = LayerContext(0, stack_context)
layer = compile0_prototype(protocol, layer_context)
block = compile5_layer(layer, layer_context)
for instr in block.instr_list:
    print(instr.compile7)
