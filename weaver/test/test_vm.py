import pytest
from weaver.vm import (
    RegStore, Reg, Unsigned, EvalEnv, NotConstant, ConstUnsigned, ConstBool,
    UnsignedRegAssertFork
)


def test_vm_conceptually():
    store = RegStore({
        Reg(0): Unsigned(2),
        Reg(1): Unsigned(2),
    })
    env = EvalEnv()
    with pytest.raises(NotConstant):
        store.get_reg(Reg(0)).load().evaluate(env)

    env.set_reg(Reg(0), Unsigned(2).const(2020))
    load_val = store.get_reg(Reg(0)).load().evaluate(env)
    assert isinstance(load_val, ConstUnsigned)
    assert load_val.value == 2020

    equal_val = store.get_reg(Reg(0)).equals_to(Unsigned(2).const(2020)).evaluate(env)
    assert isinstance(equal_val, ConstBool)
    assert equal_val.value

    fork = UnsignedRegAssertFork(store.get_reg(Reg(1)).is_one())
    fork.asserted(env)
    assert isinstance(env.get_reg(Reg(1)), ConstUnsigned)
    assert env.get_reg(Reg(1)).value == 1
