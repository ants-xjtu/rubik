import importlib
import sys
from weaver.writer_context import GlobalContext


conf = importlib.import_module(sys.argv[1])
stack = conf.stack
stack_entry = conf.stack_entry
stack_map = conf.stack_map

nexti_map = {}
compiled = {}
for name, allocated_bundle in stack.items():
    compiled[name] = allocated_bundle.compile_bundle(name, stack_map.get(name, None))
    compiled[name].register_nexti(nexti_map)

context = GlobalContext({nexti: compiled[name].recurse for nexti, name in nexti_map.items()})
for bundle in compiled.values():
    bundle.execute(context)
context.execute_all()

print('/* Weaver Whitebox Code Template */')
print(context.write_template())
print('/* Weaver Auto-generated Blackbox Code */')
print(context.write_all(compiled[stack_entry].recurse))
