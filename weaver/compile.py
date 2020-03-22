"""
compile (almost) everything
currently there are 7 different compilation stages and 2 evaluation stages
compile1: allocate header structs and field registers, generate low level header actions
  signature: (LayerContext) -> [low level header actions (which impl compile7)] (aka scanner)
compile2: allocate temp and perm variables in context, and set context attributes
  signature: (LayerContext) -> None
compile3: generate instance helper struct
  signature: (Prototype, LayerContext) -> Inst/BiInst (which impl compile5)
compile4: generate content for expressions
  signature: (LayerContext) -> weaver.prog.Expr (which impl eval1 and compile6)
compile5: generate content for statements
  signature: (LayerContext) -> weaver.prog.UpdateReg/Branch (which impl eval2 and compile7)
NOTICE: compile6 is generated in compile4 stage, so as compile7 in compile5
NOTICE: compile7 of Branch is statically generated and there's no interface to customize it
eval1: (try to) evaluate expression
  signature: (EvalContext) -> <python object represents value> throws weaver.prog.NotConstant
eval2: (try to) evaluate statement, statically implemented in weaver.prog
  signature: (EvalContext) -> None
eval3: assert an expression to be true, and modify context according to it
  signature: (EvalContext) -> None
compile6: generated C code for expression
  signature: (<str for valid C code>, <str for debug info>)
CAUTION: this signature has been proved to be a bad design, because when a single string is
accidentially taken place of the expected tuple, nothing but weird result is caused
compile7: generated C code for statement, without postfix '\n'
  signature: str, recommend to '// <debug info> \n<C code>', 
    or weaver.util.code_comment(<C code>, <debug info>)
NOTICE: compile1-5 also modify LayerContext to archieve non-local code generation, such as
external function declaration
NOTICE: weaver.compile generates code fragments, while weaver.compile2 build the unify code
file from all fragments, thus contains global setup code that not belongs to any single
compilable entity
NOTICE: compile7_branch and compile7_block lives in weaver.compile2 module to prevent circle dep
NOTICE: compile3a_prototype and compile5a_layer are two special functions that work on layer level
they complete stage 3 and 5 respectively for whole layer, and their signatures are a little
different to other functions in compile3 and compile5 families
"""

from weaver.prog import Expr, UpdateReg, Branch, NotConstant, Block
from weaver.compile2 import (
    compile6_inst_type,
    compile6_prefetch_type,
    compile6_content,
    compile6_need_free,
    compile6_struct_expr,
    compile6_inst_expr,
    compile6_prefetch_expr,
    compile7_decl_inst,
    compile7_decl_bi_inst,
)
from weaver.util import code_comment, comment_only, indent_join


class StackContext:
    RUNTIME, HEADER, INSTANCE, SEQUENCE = 0, 1, 2, 3

    def __init__(self):
        self.reg_count = 100
        self.struct_count = 0
        self.reg_map = {}  # reg(aka int) -> HeaderReg/TempReg/InstReg
        self.struct_map = {}  # struct(aka int) -> [reg(aka int)]
        self.call_struct = {}  # weaver.lang.Call -> struct ID (aka int)


class LayerContext:
    def __init__(self, layer_id, stack):
        self.layer_id = layer_id
        self.stack = stack
        self.var_map = {}  # var(aka Bit/AutoVar/InstVar).var_id -> reg(aka int)
        self.structs = set()
        self.inst = None
        self.perm_regs = []
        self.buffer_data = True
        self.zero_based = None
        self.layout_map = {}  # weaver.lang.layout -> reg(aka int)
        self.vexpr_map = {}  # id(<someone impl compile4>(aka expr)) -> reg(aka int)
        self.event_map = {}  # weaver.lang.Event -> var(aka Bit/AutoVar/InstVar)
        self.ntoh_map = {}  # UInt.var_id -> AutoVar

    def alloc_header_reg(self, bit, name):
        reg = HeaderReg(self.stack.reg_count, self.stack.struct_count, bit.length, name)
        self.var_map[bit.var_id] = self.stack.reg_count
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
        length_expr4 = (
            None if var.length_expr is None else var.length_expr.compile4(self)
        )
        reg = TempReg(self.stack.reg_count, var.byte_length, length_expr4, name)
        self.var_map[var.var_id] = self.stack.reg_count
        self.stack.reg_map[self.stack.reg_count] = reg
        self.stack.reg_count += 1

    def alloc_inst_reg(self, var, name):
        assert var.initial_expr is not None
        reg = InstReg(
            self.stack.reg_count, self.layer_id, var.byte_length, var.initial_expr, name
        )
        self.var_map[var.var_id] = self.stack.reg_count
        self.stack.reg_map[self.stack.reg_count] = reg
        self.perm_regs.append(self.stack.reg_count)
        self.stack.reg_count += 1

    def query(self, var):
        return self.var_map[var.var_id]

    @property
    def inst_expr6(self):
        return compile6_inst_expr(self.layer_id)

    @property
    def prefetch_expr6(self):
        return compile6_prefetch_expr(self.layer_id)

    @property
    def prealloc_expr6(self):
        return f"runtime->l{self.layer_id}_p"

    @property
    def inst_type6(self):
        return compile6_inst_type(self.layer_id)

    @property
    def prefetch_type6(self):
        return compile6_prefetch_type(self.layer_id)

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
                ");",
            ]
        )

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
    def remove_stat7(self):
        return self.remove_stat7_impl("")

    def remove_stat7_impl(self, postfix):
        return "\n".join(
            [
                f"tommy_hashdyn_remove(",
                f"  &runtime->t{self.layer_id}, l{self.layer_id}_eq, &{self.inst_expr6}->k{postfix},",
                f"  hash(&{self.inst_expr6}->k{postfix}, sizeof(L{self.layer_id}K))",
                ");",
            ]
        )

    @property
    def remove_rev_stat7(self):
        return self.remove_stat7_impl("_rev")

    @property
    def content_expr6(self):
        return compile6_content(self.layer_id)

    @property
    def need_free_expr6(self):
        return compile6_need_free(self.layer_id)


# most of variables are declared by user through Bit/UInt of layouts
# while there are still amount of variables are automatically generated
# such as "header parsed"/"event triggered" automatic variables and
# "current state" instance variables
# thus there are two variable-declaring interfaces coexist: weaver.lang.Bit/UInt
# for user and weaver.compile.AutoVar/InstVar for system
# notice there is no way to auto-generate header variables currently
class AutoVar:
    def __init__(self, byte_length, length_expr=None, var_id=None):
        self.byte_length = byte_length
        self.length_expr = length_expr
        self.var_id = var_id or object()

    def compile4(self, context):
        return compile4_var(self.var_id, context)

    @staticmethod
    def from_bit(bit):
        if isinstance(bit.length, int):
            assert bit.length % 8 == 0
            return AutoVar(bit.length // 8, None, bit.var_id)
        elif bit.length is None:
            return AutoVar(None, None, bit.var_id)
        else:
            return AutoVar(None, bit.length, bit.var_id)


class InstVar:
    def __init__(self, byte_length, initial_expr, var_id=None):
        self.byte_length = byte_length
        self.initial_expr = initial_expr
        self.var_id = var_id or object()

    def compile4(self, context):
        return compile4_var(self.var_id, context)

    @staticmethod
    def from_bit(bit):
        if bit.length is None:
            return InstVar(None, bit.init, bit.var_id)
        else:
            assert bit.length % 8 == 0
            return InstVar(bit.length // 8, bit.init, bit.var_id)


def compile4_var(var_id, context):
    reg = context.var_map[var_id]
    reg_info = context.stack.reg_map[reg]
    return Expr({reg}, Eval1Var(reg), (reg_info.expr6, "$" + reg_info.debug_name))


# ConstExpr is duplicated with weaver.lang.Const
# Const is for interface and used directly by user
# ConstExpr is for compilation and used internally by compiler
# weaver.lang should not import ConstExpr because ConstExpr is "pure" and is defined without
# necessary DSL features such as NumberOpMixin
# weaver.compile also should not import Const because it is a one-way import design
# is there any better solution?
# p.s. the comment above is elder than AutoVar/InstVar
# p.s. some compile0_XX methods defined in weaver.lang are also related to this problem
class ConstExpr:
    def __init__(self, value):
        self.value = value

    def compile4(self, context):
        return compile4_const(self.value)


# recorded register information in stack context
# header variables: Bit/UInt -> HeaderReg
# temp variables: Bit -> AutoVar -> TempReg
# instance variables: Bit -> InstVar -> InstReg
# NOTICE (expr6, debug_name) works as compile6 result because of hitorical issues
class HeaderReg:
    def __init__(self, reg_id, struct_id, bit_length, debug_name):
        self.reg_id = reg_id
        self.struct_id = struct_id
        self.debug_name = debug_name
        self.bit_length = bit_length

        self.expr6 = f"{compile6_struct_expr(self.struct_id)}->_{self.reg_id}"


class TempReg:
    def __init__(self, reg_id, byte_length, length_expr4, debug_name):
        self.reg_id = reg_id
        self.byte_length = byte_length
        self.debug_name = debug_name
        self.length_expr4 = length_expr4

        self.expr6 = f"_{self.reg_id}"


class InstReg:
    def __init__(self, reg_id, layer_id, byte_length, initial_expr, debug_name):
        self.reg_id = reg_id
        self.layer_id = layer_id
        self.byte_length = byte_length
        self.initial_expr = initial_expr
        self.debug_name = debug_name

        self.expr6 = f"{compile6_inst_expr(self.layer_id)}->_{self.reg_id}"


# header actions
class LocateStruct:
    def __init__(self, struct_id, struct_length, parsed_reg):
        self.compile7 = "\n".join(
            [
                f"{compile6_struct_expr(struct_id)} = (WV_Any)current.cursor;",
                f"current = WV_SliceAfter(current, {struct_length});",
                f"{parsed_reg.expr6} = 1;",
            ]
        )


class CoverSlice:
    def __init__(self, slice_reg, parsed_reg):
        self.compile7 = "\n".join(
            [
                f"{slice_reg.expr6}.cursor = current.cursor;",
                f"{slice_reg.expr6}.length = {slice_reg.length_expr4.compile6[0]}; "
                f"// {slice_reg.length_expr4.compile6[1]}",
                f"current = WV_SliceAfter(current, {slice_reg.expr6}.length);",
                f"{parsed_reg.expr6} = 1;",
            ]
        )


def compile1_layout(layout, context):
    layout_parsed_var = AutoVar(1)
    context.alloc_temp_reg(layout_parsed_var, f"parsed({layout.debug_name})")
    context.layout_map[layout] = context.query(layout_parsed_var)
    parsed_reg = context.stack.reg_map[context.query(layout_parsed_var)]

    bits_pack = []
    pack_length = 0
    struct_length = 0
    actions = []
    for name, bit in layout.field_list:
        if not isinstance(bit.length, int):
            assert pack_length == 0
            if struct_length != 0:
                struct_id = context.finalize_struct()
                actions.append(LocateStruct(struct_id, struct_length, parsed_reg))
                struct_length = 0
            context.alloc_temp_reg(
                AutoVar.from_bit(bit), layout.debug_name + "." + name
            )
            actions.append(
                CoverSlice(context.stack.reg_map[context.query(bit)], parsed_reg)
            )
        elif bit.length % 8 == 0:
            assert bits_pack == []
            context.alloc_header_reg(bit, layout.debug_name + "." + name)
            struct_length += bit.length // 8
        else:
            bits_pack.append((name, bit))
            pack_length += bit.length
            assert pack_length <= 8
            if pack_length == 8:
                bits_pack.reverse()
                for name, bit in bits_pack:
                    context.alloc_header_reg(bit, layout.debug_name + "." + name)
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


def compile1_if(if_action, context):
    return [
        ConditionalParse(
            if_action.pred.compile4(context), if_action.yes_action.compile1(context)
        )
    ]


class ConditionalParse:
    def __init__(self, pred4, scanner):
        self.compile7 = code_comment(
            f"if ({pred4.compile6[0]}) "
            + indent_join(action.compile7 for action in scanner),
            "IF " + pred4.compile6[1],
        )


class TaggedLoop:
    def __init__(self, tag_reg, scanner_map, pred4):
        # I'm lazy
        assert tag_reg.byte_length == 1
        self.compile7 = (
            "do "
            + indent_join(
                [
                    f"{tag_reg.expr6} = current.cursor[0];",
                    "current = WV_SliceAfter(current, 1);",
                    f"switch ({tag_reg.expr6}) "
                    + indent_join(
                        (f"case {value}: " if value is not None else "default: ")
                        + indent_join(
                            [*[action.compile7 for action in scanner], "break;"]
                        )
                        for value, scanner in scanner_map.items()
                    ),
                    f"// WHILE {pred4.compile6[1]}",
                ]
            )
            + f" while ({pred4.compile6[0]});"
        )


def compile1_any_until(any_until, context):
    _tag_name, tag_var = any_until.layouts[0].field_list[0]
    context.alloc_temp_reg(AutoVar.from_bit(tag_var), "tag")
    tag_reg = context.stack.reg_map[context.query(tag_var)]
    cases1 = {}
    for layout in any_until.layouts:
        _tag_name, case_tag = layout.field_list[0]
        assert case_tag.length == tag_var.length
        case_layout = lambda: None
        case_layout.field_list = layout.field_list[1:]
        case_layout.debug_name = layout.debug_name
        case_scanner = compile1_layout(case_layout, context)
        context.layout_map[layout] = context.layout_map[case_layout]
        cases1[case_tag.const] = case_scanner
    return [TaggedLoop(tag_reg, cases1, any_until.pred.compile4(context))]


# allocation and preparation
def compile2_layout(layout, context):
    for var in layout.name_map.values():
        var.compile2(context)


def compile2_header_action(action, context):
    for sub_action in action.actions:
        sub_action.compile2(context)


def compile2_uint(uint, context):
    ntoh_var = AutoVar(uint.length // 8)
    context.alloc_temp_reg(
        ntoh_var, f"ntoh({context.stack.reg_map[context.query(uint)].debug_name})"
    )
    context.ntoh_map[uint.var_id] = ntoh_var


def compile2_any_until(any_util, context):
    for layout in any_util.layouts:
        for _name, var in layout.field_list[1:]:
            var.compile2(context)


def compile2_temp_layout(layout, context):
    for name, bit in layout.name_map.items():
        context.alloc_temp_reg(AutoVar.from_bit(bit), "temp." + name)


def compile2_perm_layout(layout, context):
    for name, bit in layout.name_map.items():
        context.alloc_inst_reg(InstVar.from_bit(bit), "perm." + name)


def compile2_seq(seq, context):
    context.zero_based = seq.zero_based


def compile2_expr(expr, context):
    if expr.virtual:
        vexpr_var = InstVar(1, ConstExpr(0))
        context.alloc_inst_reg(vexpr_var, f"vexpr{len(context.vexpr_map)}")
        context.vexpr_map[id(expr)] = context.query(vexpr_var)


def compile2_if(if_stat, context):
    compile2_expr(if_stat.pred, context)
    if_stat.yes_action.compile2(context)
    if_stat.no_action.compile2(context)


def compile2_action(action, context):
    for stat in action.stats:
        stat.compile2(context)


def compile2_psm(psm, context):
    context.alloc_temp_reg(AutoVar.from_bit(psm.trans_var), "trans")
    for trans in psm.trans_list:
        compile2_expr(trans.pred, context)
        compile2_action(trans.action, context)


def compile2_call(call, context):
    for name, field in call.layout.name_map.items():
        context.alloc_header_reg(field, call.layout.debug_name + "." + name)
    struct_id = context.finalize_struct()
    context.stack.call_struct[call] = struct_id


def compile2_event_group(event_group, context):
    for name, event in event_group.name_map.items():
        var = AutoVar(1)
        context.alloc_temp_reg(var, f"event<{name}>")
        context.event_map[event] = var

        compile2_expr(event.pred, context)
        event.action.compile2(context)


# compile expressions & processing statements
def compile4_const(value):
    return Expr(set(), Eval1Const(value), (value, f"Const({value})"))


class Eval1Const:
    def __init__(self, value):
        self.value = value

    def eval1(self, context):
        return self.value


def compile4_empty():
    return Expr(set(), Eval1Empty(), ("WV_EMPTY", "EmptySlice"))


class Eval1Empty:
    def eval1(self, context):
        return []


class Eval1Var:
    def __init__(self, reg):
        self.reg = reg

    def eval1(self, context):
        if self.reg in context:
            return context[self.reg]
        else:
            raise NotConstant()


def compile5_assign(assign, context):
    reg = context.query(assign.var)
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


def compile5_if(if_stat, context):
    if if_stat.pred.virtual:
        pred = VUpdateOp(context.vexpr_map[id(if_stat.pred)], if_stat.pred)
    else:
        pred = if_stat.pred
    return [
        Branch(
            pred.compile4(context),
            if_stat.yes_action.compile5(context),
            if_stat.no_action.compile5(context),
        )
    ]


def compile5_assemble(context):
    return [
        UpdateReg(
            StackContext.SEQUENCE,
            Expr(set(), Eval1Abstract(), None),
            True,
            code_comment(
                f"{context.content_expr6} = "
                f"WV_SeqAssemble(&{context.prefetch_expr6}->seq, &{context.need_free_expr6});",
                "assemble",
            ),
        )
    ]


def compile5_call(call, context):
    return [
        UpdateReg(
            StackContext.RUNTIME,
            Expr(
                set(context.stack.struct_map[context.stack.call_struct[call]]),
                Eval1Abstract(),
                None,
            ),
            False,
            f"{call.layout.debug_name}("
            f"{compile6_struct_expr(context.stack.call_struct[call])}, "
            f"{context.inst_expr6}->user_data);",
        )
    ]


class VUpdateOp:
    def __init__(self, vexpr_reg, expr):
        self.vexpr_reg = vexpr_reg
        self.expr = expr

    def compile4(self, context):
        expr4 = self.expr.compile4(context)
        return Expr(
            {self.vexpr_reg, *expr4.read_regs},
            Eval1Abstract(),
            (
                f"WV_UpdateV(&{context.stack.reg_map[self.vexpr_reg].expr6}, "
                f"{expr4.compile6[0]}) && WV_SeqReady(&{context.prefetch_expr6}->seq)",
                f"vexpr({expr4.compile6[1]})",
            ),
        )


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
        elif self.name == "less_than":
            return expr1_eval1 < expr2_eval1
        elif self.name == "equal":
            return expr1_eval1 == expr2_eval1
        elif self.name == "and":
            return expr1_eval1 and expr2_eval1
        elif self.name == "or":
            return expr1_eval1 or expr2_eval1
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
        return f"WV_SafeAdd32({expr1}, {expr2})"
    elif name == "sub":
        return f"({expr1}) - ({expr2})"
    elif name == "left_shift":
        return f"({expr1}) << ({expr2})"
    elif name == "less_than":
        return f"({expr1}) < ({expr2})"
    elif name == "equal":
        return f"({expr1}) == ({expr2})"
    elif name == "and":
        return f"({expr1}) && ({expr2})"
    elif name == "or":
        return f"({expr1}) || ({expr2})"
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
        elif self.name == "not":
            return not expr_eval1
        else:
            assert False, f"unknown op1 {self.name}"


def compile6h_op1(name, expr):
    if name == "slice_length":
        return f"({expr}).length"
    elif name == "not":
        return f"!({expr})"
    else:
        assert False, f"unknown op1 {name}"


def compile4_header_contain(layout, context):
    return Expr(
        {StackContext.HEADER},
        Eval1Abstract(),
        (
            f"{context.stack.reg_map[context.layout_map[layout]].expr6} == 1",
            f"<layout {layout.debug_name} is parsed>",
        ),
    )


def compile4_payload():
    return Expr({StackContext.HEADER}, Eval1Abstract(), ("current", "$unparsed"))


def compile4_content(context):
    return Expr({StackContext.HEADER}, Eval1Abstract(), (context.content_expr6, "$sdu"))


def compile4_total():
    return Expr({StackContext.RUNTIME}, Eval1Abstract(), ("saved", "$total"))


def compile4_foreign_var(reg, context):
    return Expr(
        {reg},
        Eval1Abstract(),
        (
            context.stack.reg_map[reg].expr6,
            "$foreign." + context.stack.reg_map[reg].debug_name,
        ),
    )


def compile4_uint(uint, context):
    return compile4_var(context.ntoh_map[uint.var_id].var_id, context)


def compile4_var_equal(var, expr, context):
    var4 = var.compile4(context)
    reg = list(var4.read_regs)[0]
    expr4 = expr.compile4(context)
    return Expr(
        {reg, *expr4.read_regs},
        Eval1Op2("equal", var4, expr4),
        (
            compile6h_op2("equal", var4.compile6[0], expr4.compile6[0]),
            compile6h_op2("equal", var4.compile6[1], expr4.compile6[1]),
        ),
        Eval3VarEqual(reg, expr4),
    )


class Eval3VarEqual:
    def __init__(self, reg, expr):
        self.reg = reg
        self.expr = expr

    def eval3(self, context):
        try:
            context[self.reg] = self.expr.eval1(context)
        except NotConstant:
            pass


class Eval1Abstract:
    def eval1(self, context):
        raise NotConstant()


# placeholder in UpdateReg which is command
# command implements compile7 directly, so abstract_expr.compile6 should never be used
abstract_expr = Expr(set(), Eval1Abstract(), None)


# compile pipeline stages
def compile3_inst(prototype, context):
    def extract(var):
        try:
            return context.query(var)
        except AttributeError:  # foreign
            return list(var.compile4(context).read_regs)[0]

    if isinstance(prototype.selector, list):
        return Inst([extract(var) for var in prototype.selector], context.perm_regs,)
    else:
        vars1, vars2 = prototype.selector
        return BiInst(
            [extract(var) for var in vars1],
            [extract(var) for var in vars2],
            context.perm_regs,
            AutoVar.from_bit(prototype.to_active),
        )


class Inst:
    def __init__(self, key_regs, inst_regs):
        self.key_regs = key_regs
        self.inst_regs = inst_regs
        self.prefetch = PrefetchInst
        self.fetch = FetchInst
        self.create = CreateInst
        self.destroy = DestroyInst
        self.decl = DeclInst

    def compile5(self, context):
        return compile5_inst(self, context)

    def compile2(self, context):
        pass

    def compile5_fetch_extra(self, context):
        return []

    def compile5_create_extra(self, context):
        return []


def compile5_inst(inst, context):
    fetch_route = [
        UpdateReg(
            StackContext.INSTANCE, abstract_expr, True, inst.fetch(context).compile7,
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
        *inst.compile5_fetch_extra(context),
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
            StackContext.INSTANCE, abstract_expr, True, inst.create(context).compile7,
        ),
        *init_stats,
        *inst.compile5_create_extra(context),
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


class DeclInst:
    def __init__(self, context):
        self.compile7 = compile7_decl_inst(context.inst, context)


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
                        f"{context.prealloc_expr6}->k._{reg} = {context.stack.reg_map[reg].expr6};",
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
                    f"WV_InitSeq(&{context.inst_expr6}->seq, {int(context.buffer_data)}, {int(context.zero_based)});",
                    f"{context.prealloc_expr6} = WV_Malloc(sizeof({context.inst_type6}));",
                    f"memset({context.prealloc_expr6}, 0, sizeof({context.inst_type6}));",
                ]
            ),
            "create instance",
        )


class BiInst:
    def __init__(self, key_regs1, key_regs2, inst_regs, to_active):
        self.key_regs1 = key_regs1
        self.key_regs2 = key_regs2
        self.inst_regs = inst_regs
        self.key_regs = key_regs1 + key_regs2
        self.prefetch = PrefetchInst  # same as Inst
        self.create = CreateBiInst
        self.fetch = FetchBiInst
        self.destroy = DestroyBiInst
        self.decl = DeclBiInst
        self.to_active = to_active

    def compile5(self, context):
        return compile5_inst(self, context)

    def compile2(self, context):
        return compile2_bi_inst(self, context)

    def compile5_fetch_extra(self, context):
        return [
            UpdateReg(
                context.query(self.to_active),
                Expr({StackContext.INSTANCE}, Eval1Abstract(), None),
                False,
                code_comment(
                    f"{context.stack.reg_map[context.query(self.to_active)].expr6} = "
                    f"{context.prefetch_expr6}->reversed;",
                    "load to_active flag from instance",
                ),
            )
        ]

    def compile5_create_extra(self, context):
        return [
            UpdateReg(
                context.query(self.to_active),
                compile4_const(0),
                False,
                code_comment(
                    f"{context.stack.reg_map[context.query(self.to_active)].expr6} = 0;",
                    "initialize $to_active flag to 0",
                ),
            ),
        ]


def compile2_bi_inst(bi_inst, context):
    context.alloc_temp_reg(bi_inst.to_active, "to_active")


class DeclBiInst:
    def __init__(self, context):
        self.compile7 = compile7_decl_bi_inst(context.inst, context)


class FetchBiInst:
    def __init__(self, context):
        self.compile7 = code_comment(
            f"{context.inst_expr6} = {context.prefetch_expr6}->reversed ? "
            f"(WV_Any)(((WV_Byte *){context.prefetch_expr6}) - sizeof({context.prefetch_type6})) : "
            f"(WV_Any){context.prefetch_expr6};",
            "fetch bidirectional instance",
        )


class CreateBiInst:
    def __init__(self, context):
        self.compile7 = code_comment(
            "\n".join(
                [
                    *[
                        code_comment(
                            f"{context.prealloc_expr6}->k_rev._{reg} = {context.stack.reg_map[reg].expr6};",
                            f"set reversed key for {context.stack.reg_map[reg].debug_name}",
                        )
                        for reg in context.inst.key_regs
                    ],
                    context.insert_stat7,
                    context.insert_rev_stat7,
                    f"{context.prefetch_expr6} = (WV_Any)({context.inst_expr6} = {context.prealloc_expr6});",
                    f"{context.inst_expr6}->flag = 0;",
                    f"{context.inst_expr6}->flag_rev = 1;",
                    f"WV_InitSeq(&{context.inst_expr6}->seq, {int(context.buffer_data)}, {int(context.zero_based)});",
                    f"WV_InitSeq(&{context.inst_expr6}->seq_rev, {int(context.buffer_data)}, {int(context.zero_based)});",
                    f"{context.prealloc_expr6} = WV_Malloc(sizeof({context.inst_type6}));",
                    f"memset({context.prealloc_expr6}, 0, sizeof({context.inst_type6}));",
                ]
            ),
            "create bidirectional instance",
        )


class DestroyBiInst:
    def __init__(self, context):
        self.compile7 = "\n".join(
            [
                context.remove_stat7,
                context.remove_rev_stat7,
                f"WV_CleanSeq(&{context.inst_expr6}->seq, {int(context.buffer_data)});",
                f"WV_CleanSeq(&{context.inst_expr6}->seq_rev, {int(context.buffer_data)});",
                f"WV_Free({context.inst_expr6});",
            ]
        )


class DestroyInst:
    def __init__(self, context):
        self.compile7 = "\n".join(
            [
                context.remove_stat7,
                f"WV_CleanSeq(&{context.inst_expr6}->seq, {int(context.buffer_data)});",
                f"WV_Free({context.inst_expr6});",
            ]
        )


def compile5_scanner(scanner, context):
    return [
        UpdateReg(StackContext.HEADER, abstract_expr, False, "saved = current;"),
        UpdateReg(
            StackContext.HEADER,
            abstract_expr,
            True,
            "\n".join(
                [
                    *[
                        f"{context.stack.reg_map[layout_reg].expr6} = 0;"
                        for layout_reg in context.layout_map.values()
                    ],
                    *[action.compile7 for action in scanner],
                ]
            ),
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
        UpdateReg(
            StackContext.SEQUENCE,
            Expr({StackContext.HEADER}, Eval1Abstract(), None),
            False,
            code_comment(f"{context.content_expr6} = current;", "set SDU to payload"),
        ),
        *[
            UpdateReg(
                context.query(ntoh_var),
                Expr({context.var_map[var_id]}, Eval1Abstract(), None),
                False,
                f"{context.stack.reg_map[context.query(ntoh_var)].expr6} = "
                f"WV_NToH{ntoh_var.byte_length * 8}"
                f"({context.stack.reg_map[context.var_map[var_id]].expr6});",
            )
            for var_id, ntoh_var in context.ntoh_map.items()
        ],
    ]


def compile5_seq(seq, context):
    offset4 = seq.offset.compile4(context)
    data4 = seq.data.compile4(context)
    takeup4 = seq.takeup.compile4(context)
    buffer_data = context.buffer_data
    window_left4 = seq.window_left.compile4(context)
    window_right4 = seq.window_right.compile4(context)
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
                f"{data4.compile6[0]}, {takeup4.compile6[0]}, {int(buffer_data)}, "
                f"{window_left4.compile6[0]}, {window_right4.compile6[0]});",
                "\n".join(
                    [
                        "insert",
                        f"  OFFSET {offset4.compile6[1]}",
                        f"  DATA {data4.compile6[1]}",
                        f"  TAKEUP(0 = not set) {takeup4.compile6[1]}",
                        f"  BUFFER_DATA {buffer_data}",
                        f"  WINDOW_LEFT(0 = not set) {window_left4.compile6[1]}",
                        f"  WINDOW_RIGHT(0 = not set) {window_right4.compile6[1]}",
                    ]
                ),
            ),
        )
    ]


# allocate layer according to prototype
def compile3a_prototype(prototype, stack, layer_id, extra_event):
    context = LayerContext(layer_id, stack)
    scanner = prototype.header.compile1(context)

    prototype.header.compile2(context)
    if prototype.temp is not None:
        compile2_temp_layout(prototype.temp, context)
    if prototype.perm is not None:
        compile2_perm_layout(prototype.perm, context)
    if prototype.prep is not None:
        prototype.prep.compile2(context)
    if prototype.seq is not None:
        compile2_seq(prototype.seq, context)
    if prototype.psm is not None:
        context.alloc_inst_reg(InstVar.from_bit(prototype.current_state), "state")
        compile2_psm(prototype.psm, context)

    if prototype.selector is not None:
        assert context.inst is None
        context.inst = compile3_inst(prototype, context)
        context.inst.compile2(context)

    return Layer(
        context,
        scanner,
        prototype.current_state,
        prototype.header,
        prototype.temp,
        prototype.perm,
        prototype.prep,
        prototype.seq,
        prototype.psm,
        prototype.event,
        extra_event,
    )


class Layer:
    def __init__(
        self,
        context,
        scanner,
        state_var,
        header,
        temp,
        perm,
        general,
        seq,
        psm,
        prototype_event,
        event,
    ):
        self.context = context
        self.header = header
        self.temp = temp
        self.perm = perm
        self.scanner = scanner
        self.state_var = state_var
        self.general = general
        self.seq = seq
        self.psm = psm
        self.prototype_event = prototype_event
        self.event = event
        self.next_list = []


def compile5a_layer(layer):
    compile2_event_group(layer.prototype_event, layer.context)
    compile2_event_group(layer.event, layer.context)

    instr_list = compile5_scanner(layer.scanner, layer.context)
    if layer.context.inst is not None:
        instr_list += layer.context.inst.compile5(layer.context)
    if layer.general is not None:
        instr_list += layer.general.compile5(layer.context)
    if layer.seq is not None:
        instr_list += compile5_seq(layer.seq, layer.context)
    if layer.psm is not None:
        instr_list += layer.psm.compile0(layer.state_var).compile5(layer.context)

    # the more "canonical" way to compile events is:
    # 0. context.event_map should store reg(aka int) as values, compile2_event_group should be
    #    implemented accordingly
    # 1. implement compile4_event_var function, which accesses context.event_map and generate
    #    weaver.prog.Expr with corresponding register like compile2_var
    # 2. create EventVar interface in weaver.lang and implement compile4 with above function
    # 3. implement compile0 method of EventGroup, which generate Action including `EventVar`s
    # do so if necessary
    event_var_map = {
        event: layer.context.event_map[event]
        for event in [
            *layer.prototype_event.name_map.values(),
            *layer.event.name_map.values(),
        ]
    }
    instr_list += [
        UpdateReg(
            layer.context.query(var),
            compile4_const(0),
            False,
            f"{layer.context.stack.reg_map[layer.context.query(var)].expr6} = 0;",
        )
        for var in event_var_map.values()
    ]
    instr_list += layer.prototype_event.compile0(event_var_map).compile5(layer.context)
    instr_list += layer.event.compile0(event_var_map).compile5(layer.context)
    instr_list += compile5_finalize(layer, layer.context)
    return Block(instr_list, None, None, None)


def compile5_finalize(layer, context):
    next_list5 = compile5_next_list(layer.next_list, context)
    accept_list5 = [
        UpdateReg(
            StackContext.RUNTIME,
            abstract_expr,
            False,
            f"current = {context.content_expr6};",
        )
    ] + next_list5
    if context.inst is not None:
        accept_list5 += [
            UpdateReg(
                StackContext.INSTANCE,
                abstract_expr,
                True,
                context.inst.destroy(layer.context).compile7,
            )
        ]
    if layer.psm is not None:
        accept_list5 = [
            Branch(
                layer.psm.compile0_accept_pred(layer.state_var).compile4(context),
                accept_list5,
                [],
            )
        ]
    return accept_list5


def compile5_next_list(next_list, context):
    stats = []
    for pred, dst_layer in next_list:
        jump = UpdateReg(
            StackContext.RUNTIME,
            abstract_expr,
            True,
            code_comment(
                "\n".join(
                    [
                        "b%%BLOCK_ID%%_t = return_target;",
                        "return_target = %%BLOCK_ID%%;",
                        f"goto L{dst_layer.context.layer_id};",
                        "B%%BLOCK_ID%%_R:",
                        "return_target = b%%BLOCK_ID%%_t;",
                    ]
                ),
                f"jump to next layer #{dst_layer.context.layer_id}",
            ),
        )
        stats += [Branch(pred.compile4(context), [jump], [],)]
    return stats
