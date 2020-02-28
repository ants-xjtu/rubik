"""
compile (almost) everything
currently there are 7 different compilation stages and 2 evaluation stages
compile1: allocate header structs and field registers, generate low level header actions
  signature: (LayerContext) -> [low level header actions]
compile2: modify context only
  signature: (LayerContext) -> None
compile3: modify context and replace self
  signature: (LayerContext) -> <someone implements compile5>
compile4: generate content for expressions
  signature: (LayerContext) -> weaver.prog.Expr(..., <someone impl eval1>, compile6)
compile5: generate content for statements
  signature: (LayerContext) -> weaver.prog.UpdateReg(..., ..., ..., compile7)/weaver.prog.Branch
NOTICE: compile6 is generated in compile4 stage, so as compile7 in compile5
NOTICE: compile7 of Branch is statically generated and there's no interface to customize it
eval1: (try to) evaluate expression
  signature: (EvalContext) -> <python object represents value> throws weaver.prog.NotConstant
eval2: (try to) evaluate statement, statically implemented in weaver.prog
  signature: (EvalContext) -> None
compile6: generated C code for expression
  signature: (<str for valid C code>, <str for debug info>)
compile7: generated C code for statement, without postfix '\n'
  signature: str, recommend to '// <debug info> \n <C code>', 
    or weaver.util.code_comment(<C code>, <debug info>)
NOTICE: compile1-5 also modify LayerContext to archieve non-local code generation, such as
external function declaration
NOTICE: compile7_branch and compile7_block lives in weaver.compile2 module to prevent circle dep
NOTICE: compile3a_prototype and compile5a_layer are two special functions that work on layer level
they complete stage 3 and 5 respectively for whole layer, and their signatures are a little
different to other functions in compile3 and compile5 families
"""

from weaver.prog import Expr, UpdateReg, Branch, NotConstant, Block
from weaver.util import code_comment, comment_only


class StackContext:
    RUNTIME, HEADER, INSTANCE, SEQUENCE = 0, 1, 2, 3

    def __init__(self):
        self.reg_count = 100
        self.struct_count = 0
        self.reg_map = {}  # reg(aka int) -> HeaderReg/TempReg/InstReg
        self.struct_map = {}  # struct(aka int) -> [reg(aka int)]


class LayerContext:
    def __init__(self, layer_id, stack):
        self.layer_id = layer_id
        self.stack = stack
        self.var_map = {}  # var(aka bit) -> reg(aka int)
        self.structs = set()
        self.inst = None
        self.buffer_data = False
        self.zero_based = None
        self.layout_map = {}  # weaver.lang.layout -> reg(aka int)

    def alloc_header_reg(self, bit, name):
        reg = HeaderReg(self.stack.reg_count, self.stack.struct_count, bit.length, name)
        self.var_map[bit] = self.stack.reg_count
        self.stack.reg_map[self.stack.reg_count] = reg
        if self.stack.struct_count not in self.stack.struct_map:
            self.stack.struct_map[self.stack.struct_count] = []
            self.structs.add(self.stack.struct_count)
        self.stack.struct_map[self.stack.struct_count].append(self.stack.reg_count)
        self.stack.reg_count += 1

    def finalize_struct(self):
        self.stack.struct_count += 1
        return self.stack.struct_count - 1

    def alloc_temp_reg(self, var, name):
        if isinstance(var.length, int):
            assert var.length % 8 == 0
            reg = TempReg(self.stack.reg_count, var.length // 8, None, name)
        else:
            reg = TempReg(self.stack.reg_count, None, var.length.compile4(self), name)
        self.var_map[var] = self.stack.reg_count
        self.stack.reg_map[self.stack.reg_count] = reg
        self.stack.reg_count += 1

    def alloc_inst_reg(self, var, name):
        assert var.init is not None
        if var.length is not None:
            assert var.length % 8 == 0
            reg = InstReg(
                self.stack.reg_count, self.layer_id, var.length // 8, var.init, name
            )
        else:
            reg = InstReg(self.stack.reg_count, self.layer_id, None, var.init, name)
        self.var_map[var] = self.stack.reg_count
        self.stack.reg_map[self.stack.reg_count] = reg
        self.stack.reg_count += 1

    @property
    def inst_expr6(self):
        return compile6_inst_expr(self.layer_id)

    @property
    def prefetch_expr6(self):
        return f"l{self.layer_id}_f"

    @property
    def prealloc_expr6(self):
        return f"runtime->l{self.layer_id}_p"

    @property
    def inst_type6(self):
        return f"L{self.layer_id}I"

    @property
    def search_expr6(self):
        return "\n".join(
            [
                f"tommy_hashdyn_search(",
                f"  &runtime->t{self.layer_id}, l{self.layer_id}_eq, &{self.prealloc_expr6}->k,",
                f"  hash(&{self.prealloc_expr6}->k, sizeof(L{self.layer_id}K))",
                ")",
            ]
        )

    @property
    def insert_stat7(self):
        return self.insert_stat7_impl("")

    @property
    def insert_rev_stat7(self):
        return self.insert_stat7_impl("_rev")

    def insert_stat7_impl(self, postfix):
        return "\n".join(
            [
                f"tommy_hashdyn_insert(",
                f"  &runtime->t{self.layer_id}, &{self.prealloc_expr6}->node{postfix}, &{self.prealloc_expr6}->k{postfix},",
                f"  hash(&{self.prealloc_expr6}->k{postfix}, sizeof(L{self.layer_id}K))",
                ")",
            ]
        )


def compile6_inst_expr(layer_id):
    return f"l{layer_id}_i"


class HeaderReg:
    def __init__(self, reg_id, struct_id, bit_length, debug_name):
        self.reg_id = reg_id
        self.struct_id = struct_id
        self.debug_name = debug_name
        self.bit_length = bit_length

        self.expr6 = f"h{self.struct_id}->_{self.reg_id}"


class LocateStruct:
    def __init__(self, struct_id, struct_length, parsed_reg):
        self.compile7 = "\n".join(
            [
                f"h{struct_id} = (WV_Any)current;",
                f"current = WV_SliceAfter(current, {struct_length});",
                f"{parsed_reg.expr6} = 1;",
            ]
        )


class CoverSlice:
    def __init__(self, slice_reg, parsed_reg):
        self.compile7 = "\n".join(
            [
                f"{slice_reg.expr6}.cursor = current;",
                f"{slice_reg.expr6}.length = {slice_reg.length_expr4.compile6[0]}; "
                f"// {slice_reg.length_expr4.compile6[1]}",
                f"current = WV_SliceAfter(current, {slice_reg.expr6}.length);",
                f"{parsed_reg.expr6} = 1;",
            ]
        )


def compile1_layout(layout, context):
    layout_parsed_var = lambda: None
    layout_parsed_var.length = 8
    context.alloc_temp_reg(layout_parsed_var, f"parsed({layout.__name__})")
    context.layout_map[layout] = context.var_map[layout_parsed_var]
    parsed_reg = context.stack.reg_map[context.var_map[layout_parsed_var]]

    bits_pack = []
    pack_length = 0
    struct_length = 0
    actions = []
    for name, bit in layout.name_map.items():
        if not isinstance(bit.length, int):
            assert pack_length == 0
            if struct_length != 0:
                struct_id = context.finalize_struct()
                actions.append(LocateStruct(struct_id, struct_length, parsed_reg))
                struct_length = 0
            context.alloc_temp_reg(bit, layout.__name__ + "." + name)
            actions.append(
                CoverSlice(context.stack.reg_map[context.var_map[bit]], parsed_reg)
            )
        elif bit.length % 8 == 0:
            assert bits_pack == []
            context.alloc_header_reg(bit, layout.__name__ + "." + name)
            struct_length += bit.length // 8
        else:
            bits_pack.append((name, bit))
            pack_length += bit.length
            assert pack_length <= 8
            if pack_length == 8:
                bits_pack.reverse()
                for name, bit in bits_pack:
                    context.alloc_header_reg(bit, layout.__name__ + "." + name)
                bits_pack = []
                pack_length = 0
                struct_length += 1
    if struct_length != 0:
        struct_id = context.finalize_struct()
        actions.append(LocateStruct(struct_id, struct_length, parsed_reg))
    return actions


def compile1_header_action(action, context):
    compiled_actions = []
    for sub_action in action.actions:
        compiled_actions += sub_action.compile1(context)
    return compiled_actions


class TempReg:
    def __init__(self, reg_id, byte_length, length_expr4, debug_name):
        self.reg_id = reg_id
        self.byte_length = byte_length
        self.debug_name = debug_name
        self.length_expr4 = length_expr4

        self.expr6 = f"${self.reg_id}"


def compile2_layout(layout, context):
    for name, bit in layout.name_map.items():
        context.alloc_temp_reg(bit, "temp." + name)


def compile2_seq(seq, context):
    context.zero_based = seq.zero_based


def compile4_const(const):
    return Expr(set(), const, (const.value, f"Const({const.value})"))


def eval1_const(const):
    return const.value


def compile4_var(var, context):
    reg = context.var_map[var]
    return Expr(
        {reg},
        Eval1Var(reg),
        (
            context.stack.reg_map[reg].expr6,
            "$" + context.stack.reg_map[reg].debug_name,
        ),
    )


class Eval1Var:
    def __init__(self, reg):
        self.reg = reg

    def eval1(self, context):
        if self.reg in context:
            return context[self.reg]
        else:
            raise NotConstant()


def compile5_assign(assign, context):
    reg = context.var_map[assign.var]
    expr4 = assign.expr.compile4(context)
    text = code_comment(
        f"{context.stack.reg_map[reg].expr6} = {expr4.compile6[0]};",
        f"{context.stack.reg_map[reg].debug_name} = {expr4.compile6[1]}",
    )
    return [UpdateReg(reg, expr4, False, text)]


def compile5_action(action, context):
    action5 = []
    for stat in action.stats:
        action5 += stat.compile5(context)
    return action5


def compile4_op2(name, expr1, expr2, context):
    expr1_4 = expr1.compile4(context)
    expr2_4 = expr2.compile4(context)
    return Expr(
        expr1_4.read_regs | expr2_4.read_regs,
        Eval1Op2(name, expr1_4, expr2_4),
        (
            compile6h_op2(name, expr1_4.compile6[0], expr2_4.compile6[0]),
            compile6h_op2(name, expr1_4.compile6[1], expr2_4.compile6[1]),
        ),
    )


class Eval1Op2:
    def __init__(self, name, expr1, expr2):
        self.name = name
        self.expr1 = expr1
        self.expr2 = expr2

    def eval1(self, context):
        expr1_eval1 = self.expr1.eval1(context)
        expr2_eval1 = self.expr2.eval1(context)
        if self.name == "add":
            return expr1_eval1 + expr2_eval1
        elif self.name == "sub":
            return expr1_eval1 - expr2_eval1
        elif self.name == "left_shift":
            return expr1_eval1 << expr2_eval1
        elif self.name == "slice_before":
            return expr1_eval1[expr2_eval1:]
        elif self.name == "slice_after":
            return expr1_eval1[:expr2_eval1]
        elif self.name == "slice_get":
            return expr1_eval1[expr2_eval1]
        else:
            assert False, "unknown op2"


def compile6h_op2(name, expr1, expr2):
    if name == "add":
        return f"({expr1}) + ({expr2})"
    elif name == "sub":
        return f"({expr1}) - ({expr2})"
    elif name == "left_shift":
        return f"({expr1}) << ({expr2})"
    elif name == "slice_before":
        return f"WV_SliceBefore({expr1}, {expr2})"
    elif name == "slice_after":
        return f"WV_SliceAfter({expr1}, {expr2})"
    elif name == "slice_get":
        return f"({expr1}).cursor[{expr2}]"
    else:
        assert False, f"unknown op2 {name}"


def compile4_op1(name, expr, context):
    expr4 = expr.compile4(context)
    return Expr(
        expr4.read_regs,
        Eval1Op1(name, expr4),
        (
            compile6h_op1(name, expr4.compile6[0]),
            compile6h_op1(name, expr4.compile6[1]),
        ),
    )


class Eval1Op1:
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def eval1(self, context):
        expr_eval1 = self.expr.eval1(context)
        if self.name == "slice_length":
            return len(expr_eval1)
        else:
            assert False, f"unknown op1 {self.name}"


def compile6h_op1(name, expr):
    if name == "slice_length":
        return f"({expr}).length"
    else:
        assert False, f"unknown op1 {name}"


def compile4_header_contain(layout, context):
    return Expr(
        {StackContext.HEADER},
        Eval1Abstract(),
        code_comment(
            f"{context.stack.reg_map[context.layout_map[layout]].expr6} == 1",
            f"<layout {layout.__name__} is parsed>",
        ),
    )


def compile4_payload():
    return Expr({StackContext.HEADER}, Eval1Abstract(), ("current", "$payload"))


class Eval1Abstract:
    def eval1(self, context):
        raise NotConstant()


class InstReg:
    def __init__(self, reg_id, layer_id, byte_length, initial_expr, debug_name):
        self.reg_id = reg_id
        self.layer_id = layer_id
        self.byte_length = byte_length
        self.initial_expr = initial_expr
        self.debug_name = debug_name

        self.expr6 = f"{compile6_inst_expr(self.layer_id)}->_{self.reg_id}"


def compile3_inst(selector, layout, context):
    for name, var in layout.name_map.items():
        context.alloc_inst_reg(var, "perm." + name)
    # TODO: perm var from context

    inst_regs = [context.var_map[var] for var in layout.name_map.values()]
    if isinstance(selector, list):
        return Inst([context.var_map[var] for var in selector], inst_regs)
    else:
        vars1, vars2 = selector
        return BiInst(
            [context.var_map[var] for var in vars1],
            [context.var_map[var] for var in vars2],
            inst_regs,
        )


class Inst:
    def __init__(self, key_regs, inst_regs):
        self.key_regs = key_regs
        self.inst_regs = inst_regs
        self.prefetch = PrefetchInst
        self.fetch = FetchInst
        self.create = CreateInst

    def compile5(self, context):
        return compile5_inst(self, context)


def compile5_inst(inst, context):
    fetch_route = [
        UpdateReg(
            StackContext.INSTANCE,
            Expr(set(), Eval1Abstract(), None),
            True,
            inst.fetch(context).compile7,
        ),
        *[
            UpdateReg(
                inst_reg,
                Expr({StackContext.INSTANCE}, Eval1Abstract(), None),
                False,
                comment_only(
                    f"load {context.stack.reg_map[inst_reg].debug_name} from instance"
                ),
            )
            for inst_reg in inst.inst_regs
        ],
    ]
    init_stats = []
    for inst_reg in inst.inst_regs:
        initial_expr4 = context.stack.reg_map[inst_reg].initial_expr.compile4(context)
        init_stats.append(
            UpdateReg(
                inst_reg,
                initial_expr4,
                False,
                code_comment(
                    f"{context.stack.reg_map[inst_reg].expr6} = {initial_expr4.compile6[0]};",
                    f"initialize {context.stack.reg_map[inst_reg].debug_name} to {initial_expr4.compile6[1]}",
                ),
            )
        )
    create_route = [
        UpdateReg(
            StackContext.INSTANCE,
            Expr(set(), Eval1Abstract(), None),
            True,
            inst.create(context).compile7,
        ),
        *init_stats,
    ]
    return [
        UpdateReg(
            StackContext.INSTANCE,
            Expr(set(inst.key_regs), Eval1Abstract(), None),
            True,
            inst.prefetch(context).compile7,
        ),
        Branch(
            Expr(
                {StackContext.INSTANCE},
                Eval1Abstract(),
                (context.prefetch_expr6, "instance exist"),
            ),
            fetch_route,
            create_route,
        ),
        UpdateReg(
            StackContext.SEQUENCE,
            Expr({StackContext.INSTANCE}, Eval1Abstract(), None),
            False,
            comment_only("load sequence state from instance"),
        ),
    ]


class FetchInst:
    def __init__(self, context):
        self.compile7 = code_comment(
            f"{context.inst_expr6} = (WV_Any){context.prefetch_expr6};",
            "fetch instance",
        )


class PrefetchInst:
    def __init__(self, context):
        self.compile7 = "\n".join(
            [
                *[
                    code_comment(
                        f"{context.prealloc_expr6}._{reg} = {context.stack.reg_map[reg].expr6};",
                        f"set key for {context.stack.reg_map[reg].debug_name}",
                    )
                    for reg in context.inst.key_regs
                ],
                code_comment(
                    f"{context.prefetch_expr6} = {context.search_expr6};",
                    "prefetch instance",
                ),
            ],
        )


class CreateInst:
    def __init__(self, context):
        self.compile7 = code_comment(
            "\n".join(
                [
                    context.insert_stat7,
                    f"{context.prefetch_expr6} = (WV_Any)({context.inst_expr6} = {context.prealloc_expr6});",
                    f"WV_InitSeq(&{context.inst_expr6}, {int(context.buffer_data)}, {int(context.zero_based)});",
                    f"{context.prealloc_expr6} = WV_Malloc(sizeof({context.inst_type6}));",
                    f"memset({context.prealloc_expr6}, 0, (sizeof({context.inst_type6}));",
                ]
            ),
            "create instance",
        )


class BiInst:
    def __init__(self, key_regs1, key_regs2, inst_regs):
        self.key_regs1 = key_regs1
        self.key_regs2 = key_regs2
        self.inst_regs = inst_regs
        self.key_regs = key_regs1 + key_regs2

    def compile5(self, context):
        return compile5_inst(self, context)


def compile3a_prototype(prototype, stack, layer_id):
    context = LayerContext(layer_id, stack)
    header1 = prototype.header.compile1(context)
    if prototype.temp is not None:
        compile2_layout(prototype.temp, context)
    # TODO: collect vexpr
    if prototype.selector is not None:
        assert context.inst is None
        context.inst = compile3_inst(prototype.selector, prototype.perm, context)
    if prototype.seq is not None:
        compile2_seq(prototype.seq, context)
    return Layer(
        context, header1, prototype.preprocess, prototype.seq, prototype.psm, None
    )


class Layer:
    def __init__(self, context, header, general, seq, psm, event):
        self.context = context
        self.header = header
        self.general = general
        self.seq = seq
        self.psm = psm
        self.event = event


def compile5a_layer(layer):
    instr_list = compile5_header(layer.header, layer.context)
    if layer.context.inst is not None:
        instr_list += layer.context.inst.compile5(layer.context)
    if layer.general is not None:
        instr_list += layer.general.compile5(layer.context)
    if layer.seq is not None:
        instr_list += compile5_seq(layer.seq, layer.context)
    return Block(instr_list, None, None, None)


def compile5_header(header, context):
    return [
        UpdateReg(
            StackContext.HEADER,
            Expr(set(), Eval1Abstract(), None),
            True,
            "\n".join(action.compile7 for action in header),
        ),
        *[
            UpdateReg(
                reg,
                Expr(StackContext.HEADER, Eval1Abstract(), None),
                False,
                comment_only(
                    f"set header field ${context.stack.reg_map[reg].debug_name}"
                ),
            )
            for struct in context.structs
            for reg in context.stack.struct_map[struct]
        ],
    ]


def compile5_seq(seq, context):
    offset4 = seq.offset.compile4(context)
    data4 = seq.data.compile4(context)
    takeup4 = seq.takeup.compile4(context)
    return [
        UpdateReg(
            StackContext.SEQUENCE,
            Expr(
                offset4.read_regs | data4.read_regs | takeup4.read_regs,
                Eval1Abstract(),
                None,
            ),
            True,
            code_comment(
                f"WV_Insert(&{context.prefetch_expr6}->seq, {offset4.compile6[0]}, "
                f"{data4.compile6[0]}, {takeup4.compile6[0]}, 0, 0, 0);",
                f"insert OFFSET {offset4.compile6[1]} DATA {data4.compile6[1]} TAKEUP {takeup4.compile6[1]}",
            ),
        )
    ]
