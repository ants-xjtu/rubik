from weaver.misc.code import ip
from weaver.code import BasicBlock

b1 = BasicBlock.from_codes(ip)

for block in b1.recursive():
    print(block)
    print()

print('after')
while True:
    print('iterating')
    b2 = b1.relocate_cond().eval_reduce()
    if b2 is b1:
        break
    b1 = b2
b1 = b2
count = 0
nop_count = 0
for block in b1.recursive():
    print(block)
    print()
    count += 1
    if not block.codes and block.cond is None:
        nop_count += 1

print('count: ', count)
print('nop count: ', nop_count)
