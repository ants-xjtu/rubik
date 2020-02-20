from __future__ import annotations
from weaver.auxiliary import (
    reg_aux,
    instance as instance_table,
    sequence,
    runtime,
    header_parser,
)
from weaver.code import AggValue, If, SetValue, Command
from weaver.util import make_block

# pylint: disable = unused-wildcard-import
from weaver.header import *
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from weaver.writer_context import ValueContext, InstrContext
    from weaver.code import Reg


class ValueWriter:
    # fallback
    def write(self, context: ValueContext) -> str:
        if isinstance(context.value, AggValue):
            return AggValueWriter(context.value.agg_eval).write(context)
        else:
            return TemplateValueWriter(context.value.eval_template).write(context)

    def write_debug(self, context):
        if isinstance(context.value, AggValue):
            return AggValueWriter(context.value.agg_eval).write_debug(context)
        else:
            return TemplateValueWriter(context.value.eval_template).write_debug(context)


class TemplateValueWriter(ValueWriter):
    def __init__(self, cexpr_template: str):
        self.cexpr_template = cexpr_template

    def write(self, context: ValueContext) -> str:
        # print(repr(self.cexpr_template), context.value)
        return self.cexpr_template.format(
            *(reg_aux.write(context.instr_context, reg) for reg in context.value.regs)
        )

    def write_debug(self, context: ValueContext):
        return self.cexpr_template.format(
            *(reg_aux[reg].debug_name for reg in context.value.regs)
        )


class AggValueWriter(ValueWriter):
    def __init__(self, cexpr_template: str):
        super().__init__()
        self.cexpr_template = cexpr_template

    def write(self, context: ValueContext) -> str:
        assert isinstance(context.value, AggValue)
        values_text = (
            "(" + context.write_value(value) + ")" for value in context.value.values
        )
        return self.cexpr_template.format(*values_text)

    def write_debug(self, context: ValueContext) -> str:
        values_text = (
            "(" + context.write_value(value, debug=True) + ")"
            for value in context.value.values
        )
        return self.cexpr_template.format(*values_text)


class InstrWriter:
    # fallback
    def write(self, context: InstrContext) -> str:
        if isinstance(context.instr, If):
            text = (
                f"if ({context.write_value(context.instr.cond)}) "
                + make_block(
                    "\n".join(context.write_instr(instr) for instr in context.instr.yes)
                )
                + " else "
                + make_block(
                    "\n".join(context.write_instr(instr) for instr in context.instr.no)
                )
            )
            debug_text = f"// {context.write_value(context.instr.cond, debug=True)}\n"
            return debug_text + text
        elif isinstance(context.instr, SetValue):
            assert not isinstance(context.instr, Command)
            text = (
                f"{reg_aux.write(context, context.instr.reg)} = "
                f"({reg_aux[context.instr.reg].type_decl()})"
                f"({context.write_value(context.instr.value)});"
            )
            debug_text = (
                f"// {reg_aux[context.instr.reg].debug_name} = "
                f"{context.write_value(context.instr.value, debug=True)}\n"
            )
            return debug_text + text
        else:
            assert False, "should call `write` on subclasses"


class NoneWriter(InstrWriter):
    def write(self, context) -> str:
        return "// placeholder"


class InstExistWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        assert context.instr_context.recurse_context.inst_struct is not None
        return context.instr_context.recurse_context.prefetch_name()


class PrefetchInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        text = ""
        lid = context.recurse_context.layer_id
        pre_k = f"runtime->{context.recurse_context.prealloc()}->k"
        for reg in context.recurse_context.inst_struct.create_aux().key_regs:
            text += f"{pre_k}._{reg} = {reg_aux.write(context, reg)};\n"
        text += (
            f"{context.recurse_context.prefetch_name()} = tommy_hashdyn_search(\n"
            f"  &runtime->hash_{lid}, {context.recurse_context.eq_func_name()}, &{pre_k},\n"
            f"  hash(&{pre_k}, {context.recurse_context.key_struct_size()})\n"
            f");"
        )
        return text


class CreateInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        lid = context.recurse_context.layer_id
        pre = f"runtime->{context.recurse_context.prealloc()}"
        inst_aux = context.recurse_context.inst_struct.create_aux()
        use_data = context.recurse_context.use_data
        if not context.recurse_context.bidirection:
            return (
                f"tommy_hashdyn_insert(\n"
                + f"  &runtime->hash_{lid}, &{pre}->node, {pre},\n"
                + f"  hash(&{pre}->k, {context.recurse_context.key_struct_size()})\n"
                + f");\n"
                f"{context.recurse_context.prefetch_name()} = (WV_Any)({inst_aux.name()} = {pre});\n"
                f"WV_InitSeq(&{inst_aux.name()}->seq, {use_data}, {int(context.recurse_context.seq.zero_base)});\n"
                f"{pre} = malloc({inst_aux.sizeof()});\n"
                f"memset({pre}, 0, {inst_aux.sizeof()});"
            )
        else:
            pre_krev = pre + "->k_rev"
            return "\n".join(
                [
                    f"{pre_krev}._{reg} = {reg_aux.write(context, reg)};"
                    for reg in context.recurse_context.inst_struct.create_aux().key_regs
                ]
                + [
                    f"tommy_hashdyn_insert(",
                    f"  &runtime->hash_{lid}, &{pre}->node, {pre},",
                    f"  hash(&{pre}->k, {context.recurse_context.key_struct_size()})",
                    f");",
                    f"tommy_hashdyn_insert(",
                    f"  &runtime->hash_{lid}, &{pre}->node_rev, &{pre}->k_rev,",
                    f"  hash(&{pre}->k_rev, {context.recurse_context.key_struct_size()})",
                    f");",
                    f"{context.recurse_context.prefetch_name()} = (WV_Any)({inst_aux.name()} = {pre});",
                    f"{inst_aux.name()}->flag = 0;",
                    f"{inst_aux.name()}->flag_rev = 1;",
                    f"WV_InitSeq(&{inst_aux.name()}->seq, {use_data}, {int(context.recurse_context.seq.zero_base)});",
                    f"WV_InitSeq(&{inst_aux.name()}->seq_rev, {use_data}, {int(context.recurse_context.seq.zero_base)});",
                    f"{pre} = malloc({inst_aux.sizeof()});",
                    f"memset({pre}, 0, {inst_aux.sizeof()});",
                ]
            )


class CreateLightInstWriter(InstrWriter):
    def write(self, context: InstrWriter) -> str:
        pre = f"runtime->{context.recurse_context.prealloc()}"
        inst_aux = context.recurse_context.inst_struct.create_aux()
        if not context.recurse_context.bidirection:
            return f"{context.recurse_context.prefetch_name()} = (WV_Any)({inst_aux.name()} = {pre});"
        else:
            return (
                f"{context.recurse_context.prefetch_name()} = (WV_Any)({inst_aux.name()} = {pre});\n"
                f"{inst_aux.name()}->flag = 0;"
            )


class FetchInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert context.recurse_context.inst_struct is not None
        inst_name = context.recurse_context.inst_struct.create_aux().name()
        fetch = context.recurse_context.prefetch_name()
        if not context.recurse_context.bidirection:
            return f"{inst_name} = (WV_Any){fetch};"
        else:
            return (
                f"{inst_name} = {fetch}->reversed ? "
                f"(WV_Any)(((WV_Byte *){fetch}) - sizeof(L{context.recurse_context.layer_id}_Fetch)) : "
                f"(WV_Any){fetch};"
            )


class ToActiveWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return f"{context.instr_context.recurse_context.prefetch_name()}->reversed"


class HeaderContainWriter(ValueWriter):
    def __init__(self, struct):
        self.struct = struct

    def write(self, context: ValueContext) -> str:
        return self.struct.create_aux().parse_flag()


class InsertWriter(InstrWriter):
    def __init__(self, force_nodata=False):
        super().__init__()
        self.force_nodata = force_nodata

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        # assert instance_table in context.instr.args[0].regs
        assert context.recurse_context.inst_struct is not None
        assert context.recurse_context.seq is not None
        seq = context.recurse_context.seq
        return (
            f"WV_Insert("
            f"&{context.recurse_context.prefetch_name()}->seq, "
            f"{context.write_value(seq.offset)}, "
            f"{context.write_value(seq.data)}, "
            f"{context.write_value(seq.takeup)}, "
            f'{"0" if self.force_nodata else context.recurse_context.use_data}, '
            f"{context.write_value(seq.window[0])}, "
            f"{context.write_value(seq.window[1])}"
            f");"
        )


class SeqReadyWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        assert sequence in context.value.regs
        assert context.instr_context.recurse_context.inst_struct is not None
        return f"WV_SeqReady(&{context.instr_context.recurse_context.prefetch_name()}->seq)"


class SeqAssembleWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == sequence
        assert context.recurse_context.inst_struct is not None
        return (
            f"{context.recurse_context.content_name()} = WV_SeqAssemble("
            f"&{context.recurse_context.prefetch_name()}->seq, "
            f"&nf{context.recurse_context.layer_id});"
        )


class ContentWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return context.instr_context.recurse_context.content_name()


class SetContentWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        return f"{context.recurse_context.content_name()} = {context.write_value(context.instr.args[0])};"


class EmptyAlignWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return (
            f"WV_SeqEmptyAlign("
            f"&{context.instr_context.recurse_context.prefetch_name()}->seq, "
            f"{context.write_value(context.instr_context.recurse_context.seq.offset)}, "
            f"{context.write_value(context.instr_context.recurse_context.seq.data)}, "
            f"{context.write_value(context.instr_context.recurse_context.seq.takeup)}"
            f")"
        )


class DestroyInstWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == instance_table
        lid = context.recurse_context.layer_id
        prefetch = context.recurse_context.prefetch_name()
        use_data = context.recurse_context.use_data
        if not context.recurse_context.bidirection:
            return (
                f"tommy_hashdyn_remove(\n"
                f"  &runtime->hash_{lid}, {context.recurse_context.eq_func_name()}, {prefetch},\n"
                f"  hash(&{prefetch}->k, {context.recurse_context.key_struct_size()})\n"
                f");\n"
                f"WV_CleanSeq(&{prefetch}->seq, {use_data});\n"
                f"free({prefetch});"
            )
        else:
            inst = context.recurse_context.inst_struct.create_aux().name()
            return "\n".join(
                [
                    f"tommy_hashdyn_remove(",
                    f"  &runtime->hash_{lid}, {context.recurse_context.eq_func_name()}, {inst},",
                    f"  hash(&{inst}->k, {context.recurse_context.key_struct_size()})",
                    f");",
                    f"tommy_hashdyn_remove(",
                    f"  &runtime->hash_{lid}, {context.recurse_context.eq_func_name()}, &{inst}->k_rev,",
                    f"  hash(&{inst}->k_rev, {context.recurse_context.key_struct_size()})",
                    f");",
                    f"WV_CleanSeq(&{inst}->seq, {use_data});",
                    f"WV_CleanSeq(&{inst}->seq_rev, {use_data});",
                    f"free({inst});",
                ]
            )


class NextWriter(InstrWriter):
    def __init__(self, recursive):
        super(NextWriter, self).__init__()
        self.recursive = recursive

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == runtime
        context.recurse_context.global_context.required_return_blocks.add(context.block)
        next_entry = context.recurse_context.global_context.next_table[
            context.instr
        ].block_id
        content = context.instr.args[0]
        if not self.recursive:
            return (
                f"current = {context.write_value(content)};\n"
                + f"saved_target_{context.block.block_id} = ret_target;\n"
                + f"ret_target = {context.block.block_id}; goto L{next_entry}; NI{context.block.block_id}_Ret:\n"
                + f"ret_target = saved_target_{context.block.block_id};"
            )
        else:
            return (
                f"current = {context.write_value(content)};\n" + f"goto L{next_entry};"
            )


class ParseHeaderWriter(InstrWriter):
    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == header_parser
        return "saved = current;\n" + self.write_actions(
            context.recurse_context.actions, context
        )

    def write_actions(self, actions: List[ParseAction], context: InstrContext) -> str:
        lines = []
        for action in actions:
            if isinstance(action, LocateStruct):
                lines.append(
                    f"{action.struct.create_aux().name()} = (WV_Any)current.cursor;"
                )
                lines.append(f"{action.struct.create_aux().parse_flag()} = 1;")
                lines.append(
                    f"current = WV_SliceAfter(current, {action.struct.byte_length});"
                )
            elif isinstance(action, ParseByteSlice):
                assert reg_aux[action.slice_reg].byte_len is None
                reg_text = reg_aux.write(context, action.slice_reg)
                lines.append(f"{reg_text}.cursor = current.cursor;")
                lines.append(
                    f"{reg_text}.length = {context.write_value(action.byte_length)};"
                )
                lines.append(f"current = WV_SliceAfter(current, {reg_text}.length);")
            elif isinstance(action, TaggedParseLoop):
                assert reg_aux[action.tag].byte_len == 1  # no ntoh issue
                tag_text = reg_aux.write(context, action.tag)
                lines.append(
                    "do "
                    + make_block(
                        "\n".join(
                            [
                                f"{tag_text} = (({reg_aux[action.tag].type_decl()} *)current.cursor)[0];",
                                f"current = WV_SliceAfter(current, {reg_aux[action.tag].byte_len});",
                                f"switch ({tag_text}) "
                                + make_block(
                                    "\n".join(
                                        (
                                            f"case {match}: "
                                            if match is not None
                                            else "default: "
                                        )
                                        + make_block(
                                            self.write_actions(actions, context)
                                            + "\ncontinue;"
                                        )
                                        for match, actions in action.action_map.items()
                                    )
                                ),
                            ]
                        )
                    )
                    + f" while ({context.write_value(action.cond)});"
                )
            elif isinstance(action, OptionalActions):
                lines.append(
                    f"if ({context.write_value(action.cond)}) "
                    + make_block(self.write_actions(action.actions, context))
                )
            else:
                assert False
        return "\n".join(lines)


class CallWriter(InstrWriter):
    def __init__(self, name: str, regs: List[Reg] = None):
        super(CallWriter, self).__init__()
        self.name = name
        self.regs = regs or []

    def write(self, context: InstrContext) -> str:
        assert isinstance(context.instr, Command)
        assert context.instr.provider == runtime
        context.recurse_context.global_context.required_calls[self.name] = self.regs
        if context.recurse_context.inst_struct is not None:
            userdata_text = "&" + context.recurse_context.prefetch_name() + "->userdata"
        else:
            userdata_text = "NULL"
        return f'{self.name}({", ".join([reg_aux.write(context, reg) for reg in self.regs] + [userdata_text])});'


class PayloadWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return "current"


class PayloadLengthWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return "current.length"


class ParsedWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return "WV_SliceBefore(saved, saved.length - current.length)"


class TotalWriter(ValueWriter):
    def write(self, context: ValueContext) -> str:
        return "saved"

