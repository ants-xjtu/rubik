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
print('after relocate')
for block in b1.relocate_cond().recursive():
    print(block)
    print()
print('after evaluate')
for block in b1.relocate_cond().eval_reduce().recursive():
    print(block)
    print()
