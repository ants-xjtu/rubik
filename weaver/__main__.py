from sys import argv
from importlib import import_module

from weaver.compile import (
    StackContext,
    LayerContext,
    compile3a_prototype,
    compile5a_layer,
)
from weaver.compile2 import compile7_block


protocol = import_module(argv[1]).ip_parser()
stack_context = StackContext()
layer = compile3a_prototype(protocol, stack_context, 0)
block = compile5a_layer(layer)
print(compile7_block(block))
