from weaver.code import *
from weaver.vm import *


def test_execute():
    vm = Runtime()
    vm.set_value(1000, 0)
    vm.execute(BasicBlock.from_codes([
        SetValue(1001, Value([1000], '{0} + 1')),
    ]))
    assert vm.env[1001] == 1


def test_execute_command():
    class Parser(CommandExecutor):
        def execute(self, command: str, args: List[Any], runtime: Runtime):
            if command == 'Parse':
                assert args == []
                runtime.set_value(1000, 0)
            else:
                assert False, f'unknown command {command}'

    vm = Runtime()
    vm.register(0, Parser())
    vm.execute(BasicBlock.from_codes([
        Command(0, 'Parse', []),
        SetValue(1001, Value([1000], '{0} + 1')),
    ]))
    assert vm.env[1001] == 1
