from weaver.code import *


def test_build_basic_block():
    b1 = BasicBlock.from_codes([])


def test_relocate():
    create = Command(0, 'Create', [])
    destroy = Command(0, 'Destroy', [], opt_target=True)
    b1 = BasicBlock.from_codes([
        create,
        If(Value([1], '{0}'), [
            destroy,
        ])
    ]).optimize()
    assert any(all(instr in block.codes for instr in [create, destroy]) for block in b1.recurse())
