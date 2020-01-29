from weaver.stock.protocols.tcp_ip import ip
from weaver.writer_context import GlobalContext

bundle = ip().compile_bundle()
# for instr in bundle.codes:
#     print(instr)
cxt = GlobalContext({})
bundle.execute(cxt)
cxt.execute_all()

print('/* Weaver Whitebox Code Template */')
print(cxt.write_template())
print('/* Weaver Auto-generated Blackbox Code */')
print(cxt.write_all(bundle.recurse))
