from weaver.code import *

b1 = BasicBlock.from_codes([
    SetValue(0, Value([], '2')),
    SetValue(1, Value([0], '{0} + {0}')),
    SetValue(2, Value([0, 1], '{0} + {1}')),
    If(Value([2], '{0} > 3'), [
        SetValue(2, Value([2, 1], '{0} - {1}')),
    ], []),
    If(Value([2], '{0} > 3'), [
        SetValue(2, Value([2, 0], '{0} - {1}')),
    ], []),
])

for block in b1.recursive():
    print(block)
    print()
print('after')
for block in b1.eval_reduce().recursive():
    print(block)
    print()
