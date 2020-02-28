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
