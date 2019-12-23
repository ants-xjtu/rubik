from weaver.code import *

b1 = BasicBlock.from_codes([
    SetValue(1, Value([], '1')),
    SetValue(2, Value([0, 1], '{0} + {1}')),
    If(EqualTest(0, Value([], '4')), [
        SetValue(2, Value([2, 1], '{0} - {1}')),
    ], []),
    If(EqualTest(2, Value([], '4')), [
        SetValue(2, Value([2, 1], '{0} - {1}')),
    ], [
        SetValue(2, Value([2, 1], '{0} + {1}')),
    ]),
])

for block in b1.recursive():
    print(block)
    print()

print('after')
while True:
    b2 = b1.relocate_cond().eval_reduce()
    if b2 is b1:
        break
    b1 = b2
b1 = b2
for block in b1.recursive():
    print(block)
    print()
