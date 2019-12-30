def make_block(text: str) -> str:
    if text:
        text = ('\n' + text).replace('\n', '\n  ') + '\n'
    return '{' + text + '}'
