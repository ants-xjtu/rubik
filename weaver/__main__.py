from weaver.misc.code import *
from weaver.code import *

b1 = BasicBlock.from_codes(ip)

for block in b1.recursive():
    print(block)
    print()
print('Used block count: ', BasicBlock.count)

while True:
    print('iterating')
    b2 = b1.eval_reduce()
    print('evaluate: ', b2 is not b1)
    b3 = b2.relocate_cond()
    print('relocate: ', b3 is not b2)
    if b3 is b1:
        break
    b1 = b3
b1 = b3
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
