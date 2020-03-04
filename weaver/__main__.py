from sys import argv
from importlib import import_module

from weaver.compile import (
    StackContext,
    LayerContext,
    compile3a_prototype,
    compile5a_layer,
)
from weaver.compile2 import compile7_block


stack = import_module(argv[1]).stack
print(compile7_block(compile5a_layer(stack.ip.layer)))
