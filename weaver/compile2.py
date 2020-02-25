from weaver.util import indent_join, make_block


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
    return f"{prefix} _{reg.reg_id}{postfix};  // {reg.debug_name}"


def compile7_stack(stack, blocks, inst_decls, layer_count):
    prefix7 = "\n".join(
        [
            "#include <weaver.h>",
            "#include <tommyds/tommyhashdyn.h>",
            "#if TOMMY_SIZE_BIT == 64",
            "#define hash(k, s) tommy_hash_u64(0, k, s)",
            "#else",
            "#define hash(k, s) tommy_hash_u32(0, k, s)",
            "#endif",
        ]
    )

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

    inst_structs7 = "\n".join(inst_decl.compile7 for inst_decl in inst_decls.values())

    eq_func7 = "\n".join(
        f"int l{i}_eq(const void *key, const void *object) "
        + make_block(f"return memcmp(key, object, sizeof({compile6_key_type(i)}));")
        for i in range(layer_count)
        if i in inst_decls
    )

    runtime7 = "\n".join(
        [
            "struct _WV_Runtime "
            + indent_join(
                [
                    "WV_Profile profile;",
                    *[
                        f"{compile6_inst_type(i)} *l{i}_p;\n" + f"tommy_hashdyn t{i};"
                        for i in range(layer_count)
                        if i in inst_decls
                    ],
                ]
            )
            + ";",
            "WV_Runtime *WV_AllocRuntime() "
            + indent_join(
                [
                    "WV_Runtime *rt = WV_Malloc(sizeof(WV_Runtime));",
                    *[
                        "\n".join(
                            [
                                f"tommy_hashdyn_init(&rt->t{i});",
                                f"rt->l{i}_p = WV_Malloc(sizeof({compile6_inst_type(i)}));",
                                f"memset(rt->l{i}_p, 0, sizeof({compile6_inst_type(i)}));",
                            ]
                        )
                        for i in range(layer_count)
                        if i in inst_decls
                    ],
                    "return rt;",
                ]
            ),
            "WV_U8 WV_FreeRuntime(WV_Runtime *rt) " + make_block("// todo\nreturn 0;"),
            "WV_Profile *WV_GetProfile(WV_Runtime *rt) "
            + make_block("return &rt->profile;"),
        ]
    )

    raw_blocks7 = {block.block_id: compile7_block(block) for block in blocks}
    blocks7 = {
        block_id: block7.replace("%%BLOCK_ID%%", str(block_id))
        for block_id, block7 in raw_blocks7.items()
    }

    process7 = (
        "WV_U8 WV_ProcessPacket(WV_ByteSlice packet, WV_Runtime *runtime) "
        + indent_join(
            [
                *[f"H{struct} *h{struct};" for struct in stack.struct_map],
                *[
                    f"WV_ByteSlice l{layer}_c;\n" + f"WV_Byte *l{layer}_nf = NULL;"
                    for layer in range(layer_count)
                ],
                *[
                    f"{compile6_inst_type(layer)} *l{layer}_i;\n"
                    + f"{compile6_prefetch_type(layer)} *l{layer}_f;"
                    for layer in range(layer_count)
                    if layer in inst_decls
                ],
                *[
                    f"WV_U8 b{block.block_id}_t;"
                    for block in blocks
                    if raw_blocks7[block.block_id] != blocks7[block.block_id]
                ],
                *[
                    decl_reg(reg, "$")
                    for reg in stack.reg_map.values()
                    # todo
                    if not hasattr(reg, "layer_id") and not hasattr(reg, "struct_id")
                ],
                "WV_ByteSlice current = packet, saved;",
                "WV_I32 return_target = -1;",
                "L_Shower: "
                + make_block(
                    "switch (return_target) "
                    + indent_join(
                        [
                            *[
                                f"case {block.block_id}: goto B{block.block_id}_R;"
                                for block in blocks
                                if raw_blocks7[block.block_id]
                                != blocks7[block.block_id]
                            ],
                            "default: goto L_End;",
                        ]
                    )
                ),
                "L_End: "
                + indent_join(
                    [
                        *[
                            f"if (l{layer}_nf) WV_Free(l{layer}_nf);"
                            for layer in range(layer_count)
                        ],
                        "return 0;",
                    ]
                ),
                *blocks7.values(),
            ]
        )
    )

    return "\n".join(
        [prefix7, struct7, extern_call7, inst_structs7, eq_func7, runtime7, process7]
    )


def compile7w_stack(stack):
    setup7 = "WV_U8 WV_Setup() " + make_block("return 0;")

    extern_call7 = "\n".join(
        "typedef struct "
        + indent_join(
            decl_header_reg(stack.reg_map[reg]) for reg in stack.struct_map[struct_id]
        )
        + f" H{struct_id};\n"
        + f"WV_U8 {call.layout.debug_name}(H{struct_id} *args, WV_Any user_data) "
        + make_block("return 0;")
        for call, struct_id in stack.call_struct.items()
    )
    return "\n".join(["#include <weaver.h>", setup7, extern_call7])


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
    return f"{type_decl} {prefix}{reg.reg_id};  // {reg.debug_name}"


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
                f"{compile6_rev_key_type(context.layer_id)} k_rev;",
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
                "WV_U8 reversed;",
                "tommy_node node;",
                "WV_Seq seq;",
                "WV_Any user_data;",
            ]
        )
        + f" {compile6_prefetch_type(context.layer_id)};"
    )