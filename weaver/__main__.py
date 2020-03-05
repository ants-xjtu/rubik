from sys import argv
from importlib import import_module

from weaver.compile import compile5a_layer
from weaver.compile2 import compile7_stack


stack = import_module(argv[1]).stack
blocks = [compile5a_layer(layer.layer) for layer in stack.name_map.values()]
inst_decls = [layer.layer.context.inst.decl(layer.layer.context) for layer in stack.name_map.values()]
print(compile7_stack(stack.context, blocks, inst_decls))
