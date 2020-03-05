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


def decl_header_reg(reg):
    if reg.bit_length is None:  # only in event layout
        prefix = "WV_ByteSlice"
        postfix = ""
    elif reg.bit_length < 8:
        prefix = "WV_U8"
        postfix = f": {reg.bit_length}"
    else:
        prefix = f"WV_U{reg.bit_length}"
        postfix = ""
    return f"{prefix} _{reg.reg_id}{postfix};"


def compile7_stack(stack, blocks, inst_decls):
    layers7 = "\n".join(compile7_block(block) for block in blocks)

    struct7 = "\n".join(
        "typedef struct "
        + indent_join(decl_header_reg(stack.reg_map[reg]) for reg in regs)
        + f" H{struct};"
        for struct, regs in stack.struct_map.items()
    )

    extern_call7 = "\n".join(
        f"WV_U8 {call.layout.debug_name}(H{struct_id} *, WV_Any);"
        for call, struct_id in stack.call_struct.items()
    )

    inst_structs7 = "\n".join(inst_decl.compile7 for inst_decl in inst_decls)

    return struct7 + "\n" + extern_call7 + "\n" + inst_structs7


def compile6_inst_type(layer_id):
    return f"L{layer_id}I"


def compile6_key_type(layer_id):
    return f"L{layer_id}K"


def compile6_rev_key_type(layer_id):
    return f"L{layer_id}RK"


def compile6_prefetch_type(layer_id):
    return f"L{layer_id}F"


def decl_reg(reg, prefix="_"):
    if reg.byte_length is not None:
        type_decl = f"WV_U{reg.byte_length * 8}"
    else:
        type_decl = "WV_ByteSlice"
    return f"{type_decl} {prefix}{reg.reg_id};"


def compile7_decl_inst(inst, context):
    return (
        "typedef struct "
        + indent_join(
            decl_header_reg(context.stack.reg_map[reg]) for reg in inst.key_regs
        )
        + f" {compile6_key_type(context.layer_id)};\n"
        + "typedef struct "
        + indent_join(
            [
                f"{compile6_key_type(context.layer_id)} k;",
                "tommy_node node;",
                "WV_Seq seq;",
                "WV_Any user_data;",
                *[decl_reg(context.stack.reg_map[reg]) for reg in inst.inst_regs],
            ]
        )
        + f" {compile6_inst_type(context.layer_id)}, {compile6_prefetch_type(context.layer_id)};"
    )


def compile7_decl_bi_inst(bi_inst, context):
    return (
        "typedef struct "
        + indent_join(
            decl_header_reg(context.stack.reg_map[reg])
            for reg in bi_inst.key_regs1 + bi_inst.key_regs2
        )
        + f" {compile6_key_type(context.layer_id)};\n"
        + "typedef struct "
        + indent_join(
            decl_header_reg(context.stack.reg_map[reg])
            for reg in bi_inst.key_regs2 + bi_inst.key_regs1
        )
        + f" {compile6_rev_key_type(context.layer_id)};\n"
        + "typedef struct "
        + indent_join(
            [
                f"{compile6_key_type(context.layer_id)} k;",
                "WV_U8 flag;",
                "tommy_node node;",
                "WV_Seq seq;",
                "WV_Any user_data;",
                f"{compile6_rev_key_type(context.layer_id)} k;",
                "WV_U8 flag_rev;",
                "tommy_node node_rev;",
                "WV_Seq seq_rev;",
                "WV_Any user_data_rev;",
                *[decl_reg(context.stack.reg_map[reg]) for reg in bi_inst.inst_regs],
            ]
        )
        + f" {compile6_inst_type(context.layer_id)};\n"
        + "typedef struct "
        + indent_join(
            [
                f"{compile6_key_type(context.layer_id)} k;",
                "WV_U8 flag;",
                "tommy_node node;",
                "WV_Seq seq;",
                "WV_Any user_data;",
            ]
        )
        + f" {compile6_prefetch_type(context.layer_id)};"
    )
