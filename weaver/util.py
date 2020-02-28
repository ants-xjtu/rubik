def make_block(text: str) -> str:
    if text:
        text = ("\n" + text).replace("\n", "\n  ") + "\n"
    return "{" + text + "}"


def indent_join(text_list):
    return make_block("\n".join(text_list))


def code_comment(text, comment):
    return f"// {comment}\n{text}"


def comment_only(comment):
    return f"// LOGICALLY {comment}"

