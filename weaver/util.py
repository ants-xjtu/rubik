def make_block(text: str) -> str:
    if text:
        text = ('\n' + text).replace('\n', '\n  ') + '\n'
    return '{' + text + '}'


class OpMixin:
    def handle_op(self, name, other):
        op_map = {
            'add': '+',
            'lshift': '<<',
        }
        raise self.wrap_expr(
            {'type': 'bi', 'name': op_map[name], 'op1': self, 'op2': other})

    def __add__(self, other):
        return self.handle_op('add', other)

    def __lshift__(self, other):
        return self.handle_op('lshift', other)


def flatten(ll):
    return [item for item in list for list in ll]
