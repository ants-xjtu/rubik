from weaver.code import *

b1 = BasicBlock.from_codes([
    SetValue(1, Value([], '1')),
    SetValue(2, Value([0, 1], '{0} + {1}')),
    If(EqualTest(2, Value([], '4')), [
        SetValue(2, Value([2, 1], '{0} - {1}')),
    ], []),
    If(EqualTest(2, Value([], '3')), [
        SetValue(2, Value([2, 1], '{0} - {1}')),
    ], [
        SetValue(2, Value([2, 1], '{0} + {1}')),
    ]),
])

for block in b1.recursive():
    print(block)
    print()
print('after')
for block in b1.eval_reduce().recursive():
    print(block)
    print()
