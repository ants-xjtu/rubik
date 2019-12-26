def make_block(text):
    if text:
        text = ('\n' + text).replace('\n', '\n  ') + '\n'
    return '{' + text + '}'