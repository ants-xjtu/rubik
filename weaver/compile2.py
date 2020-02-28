from weaver.util import indent_join


def compile7_branch(branch):
    return "\n".join(
        [
            f"// IF {branch.pred.compile6[1]}",
            f"if ({branch.pred.compile6[0]}) "
            + indent_join(stat.compile7 for stat in branch.yes_list)
            + " else "
            + indent_join(stat.compile7 for stat in branch.no_list),
        ]
    )


def compile7_block(block):
    if block.pred is not None:
        escape = (
            f"if ({block.pred.compile6}) goto L{block.yes_block.block_id}; "
            "else goto L{block.no_block.block_id};"
        )
    else:
        escape = "goto L_Shower;"
    return f"L{block.block_id}: " + indent_join(
        [*[instr.compile7 for instr in block.instr_list], escape]
    )

