# pylint: disable = unused-wildcard-import
from weaver.code import *
from weaver.writer import *
from weaver.stock import header
from weaver.stock.reg import *
from weaver.stock import make_reg
from weaver.lang import *
from typing import List

# common:
yes = Value([], '1')
no = Value([], '0')
ready = Value([sequence], 'seq->ready', SeqReadyWriter())

# Ethernet protocol
next_ip = Command(runtime, 'Next', [], opt_target=True, aux=NextWriter())
eth: List[Instr] = [
    Command(header_parser, 'Parse', [], aux=ParseHeaderWriter()),
    Command(runtime, 'Call', [Value([header.eth_type])],
            aux=CallWriter('check_eth_type', [header.eth_type])),
    If(Value([header_parser, header.eth_type], 'WV_NToH16({1}) == 0x0800'), [
        next_ip,
    ]),
]

# IP protocol
# header.tcp_data_state = make_reg(1000, 1)
psm_triggered = make_reg(2000, 1)
psm_trans = make_reg(2001, 2)

saddr = Value([header_parser, header.ip_src], '{1}')
daddr = Value([header_parser, header.ip_dst], '{1}')
DUMP = Value([], '0')
FRAG = Value([], '1')
dump = Value([], '0')
frag = Value([], '1')
last = Value([], '2')
more = Value([], '3')
dont_frag = Value([header_parser, header.ip_dont_frag], '{1}')
more_frag = Value([header_parser, header.ip_more_frag], '{1}')
seen_dont_frag = make_reg(1001, 1)
offset = make_reg(2002, 2)
payload = make_reg(2003)
next_tcp = Command(runtime, 'Next', [], opt_target=True, aux=NextWriter(True))
ip: List[Instr] = [
    Command(header_parser, 'Parse', [], aux=ParseHeaderWriter()),
    Command(instance_table, 'Prefetch', [
            saddr, daddr], aux=PrefetchInstWriter()),
    If(AggValue([Value([instance_table])], 'InstExist()', InstExistWriter()), [
        Command(instance_table, 'Fetch', [], aux=FetchInstWriter()),
    ], [
        Command(instance_table, 'Create', [],
                opt_target=True, aux=CreateInstWriter()),
        SetValue(header.ip_state, DUMP),
        SetValue(header.ip_expr1, no),
    ]),
    SetValue(offset, Value([header_parser, header.ip_offset1,
                            header.ip_offset2], '(({1} << 8) + {2}) << 3')),
    SetValue(payload,
             AggValue([
                 Value([header_parser, header.ip_len], '{1}'),
                 Value([header_parser, header.ip_ihl], '{1}'),
                 Value([header_parser], aux=PayloadWriter())
             ],
                 '(WV_ByteSlice){{ .cursor = {2}.cursor, .length = WV_NToH16({0}) - ({1} << 2) }}')),
    Command(sequence, 'InsertMeta',
            [Value([instance_table]), Value([offset], '{0}'),
             Value([payload], '{0}')],
            opt_target=True, aux=InsertWriter()),
    SetValue(psm_triggered, no),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.ip_state, DUMP), [
            If(dont_frag, [
                SetValue(psm_trans, dump),
                SetValue(header.ip_state, DUMP),
                SetValue(psm_triggered, yes),
            ]),
            If(more_frag, [
                SetValue(psm_trans, more),
                SetValue(header.ip_state, FRAG),
                SetValue(psm_triggered, yes),
            ]),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.ip_state, FRAG), [
            If(AggValue([more_frag], 'not {0}', AggValueWriter('!{0}')), [
                SetValue(header.ip_expr1, yes),
            ]),
            If(EqualTest(header.ip_expr1, yes), [
                If(ready, [
                    SetValue(psm_trans, last),
                    SetValue(header.ip_state, DUMP),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            If(AggValue([EqualTest(header.ip_expr1, no), ready], '{0} or not {1}', AggValueWriter('{0} || !{1}')), [
                SetValue(psm_trans, frag),
                SetValue(header.ip_state, FRAG),
                SetValue(psm_triggered, yes),
            ]),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(header.ip_state, DUMP), [
        Command(sequence, 'Assemble', [],
                opt_target=True, aux=SeqAssembleWriter()),
    ]),
    Command(runtime, 'Call', [Value([header.ip_state], '{0}'), Value([psm_trans], '{0}')], aux=CallWriter(
        'dump_ip', [header.ip_state, psm_trans]), opt_target=True),
    If(EqualTest(header.ip_state, DUMP), [
        If(AggValue([Value([header_parser, header.ip_protocol], '{1}'), Value([], '6')], '{0} == {1}'), [
            Command(runtime, 'Call', [], aux=CallWriter(
                'count_tcp_payload'), opt_target=True),
            next_tcp,
        ]),
        Command(instance_table, 'Destroy', [],
                opt_target=True, aux=DestroyInstWriter()),
    ])
]

ip_seq = Seq(Value([offset], '{0}'), Value([payload], '{0}'))

# TCP protocol
psm_triggered = make_reg(4000, 1)
psm_trans = make_reg(4001, 2)
reg_wnd = make_reg(4002, 4)
reg_wnd_size = make_reg(4003, 4)
reg_to_active = make_reg(4004, 1)
reg_takeup = make_reg(4005, 4)
reg_data = make_reg(4006)

sport = Value([header_parser], 'header->sport')
dport = Value([header_parser], 'header->dport')
CLOSED = Value([], '0')
SYN_SENT = Value([], '1')
SYN_RECV = Value([], '2')
EST = Value([], '3')
FIN_WAIT = Value([], '4')
CLOSE_WAIT = Value([], '5')
LAST_ACK = Value([], '6')
TERMINATE = Value([], '7')
trans_fake = Value([], '0')
trans_hs1 = Value([], '1')
trans_hs2 = Value([], '2')
trans_buffering = Value([], '4')  # reorder to disable duplicate code detection
trans_hs3 = Value([], '3')
trans_wv1 = Value([], '5')
trans_wv2 = Value([], '6')
trans_wv2_fast = Value([], '7')
trans_wv3 = Value([], '8')
trans_wv4 = Value([], '9')

value_payload = Value([header_parser], 'header_meta->payload', PayloadWriter())
value_payload_len = Value(
    [header_parser], 'header_meta->payload_length', PayloadLengthWriter())
value_seq_num = Value([header_parser, header.tcp_seq], 'WV_NToH32({1})')
value_ack = Value([header_parser, header.tcp_ack], '{1}')
value_ack_num = Value([header_parser, header.tcp_acknum], 'WV_NToH32({1})')
value_syn = Value([header_parser, header.tcp_syn], '{1}')
value_fin = Value([header_parser, header.tcp_fin], '{1}')
value_to_active = Value([reg_to_active], '{0}')
value_to_passive = Value(
    [reg_to_active], 'not {0}', TemplateValueWriter('!{0}'))


def assign_data(data: Value, data_len: Value) -> List[Instr]:
    return [
        SetValue(reg_data, data),
        SetValue(reg_takeup, data_len),
    ]


def update_window(that_lwnd: int, that_wscale: int, that_wsize: int, this_lwnd: int, this_wscale: int,
                  this_wsize: int) -> List[Instr]:
    return [
        If(Value([header_parser], 'HeaderContain(tcp_ws)', HeaderContainWriter(header.tcp_header_ws)), [
            SetValue(that_wscale, Value(
                [header_parser, header.tcp_ws_value], '{1}')),
        ]),
        SetValue(that_wsize, Value(
            [header_parser, header.tcp_wndsize], 'WV_NToH16({1})')),
        SetValue(that_lwnd, value_ack_num),
        SetValue(reg_wnd, Value([this_lwnd], '{0}')),
        SetValue(reg_wnd_size, Value([this_wsize, this_wscale], '{0} << {1}')),
    ]


def to_rst(from_state: Value):
    to_state = AggValue([from_state], f'{{0}} + {TERMINATE}')
    trans = AggValue([from_state], f'{{0}} + {trans_wv4}')
    return If(Value([header_parser, header.tcp_rst], '{1}'), [
        SetValue(psm_trans, trans),
        SetValue(header.tcp_data_state, to_state),
        SetValue(psm_triggered, yes),
    ])


tcp: List[Instr] = [
    Command(header_parser, 'Parse', [], aux=ParseHeaderWriter()),
    Command(instance_table, 'Prefetch', [
            saddr, sport, daddr, dport], aux=PrefetchInstWriter()),
    If(AggValue([Value([instance_table]), saddr, sport, daddr, dport], 'InstExist({1}, {2}, {3}, {4})', aux=InstExistWriter()), [
        Command(instance_table, 'Fetch', [
                saddr, sport, daddr, dport], aux=FetchInstWriter()),
        SetValue(reg_to_active, Value(
            [instance_table], 'InstToActive()', ToActiveWriter())),
    ], [
        Command(instance_table, 'Create', [
                saddr, sport, daddr, dport], opt_target=True, aux=CreateInstWriter()),
        SetValue(reg_to_active, no),
        SetValue(header.tcp_data_state, CLOSED),
        SetValue(header.tcp_data_fin_seq_1, no),
        SetValue(header.tcp_data_fin_seq_2, no),
        SetValue(header.tcp_data_active_wsize, Value([], f'{(1 << 32) - 1}')),
        SetValue(header.tcp_data_active_wscale, no),
        SetValue(header.tcp_data_active_lwnd, no),
        SetValue(header.tcp_data_passive_wsize, Value([], f'{(1 << 32) - 1}')),
        SetValue(header.tcp_data_passive_wscale, no),
        SetValue(header.tcp_data_passive_lwnd, no),
        SetValue(header.tcp_data_seen_ack, no),
        SetValue(header.tcp_data_seen_fin, no),
        SetValue(header.tcp_data_wv2_expr, no),
        SetValue(header.tcp_data_wv2_fast_expr, no),
        SetValue(header.tcp_data_wv4_expr, no),
    ]),
    If(value_ack, assign_data(value_payload, value_payload_len), [
        If(value_syn, assign_data(Value([runtime], 'WV_EMPTY'), Value([], '1')), [
            If(value_fin, assign_data(value_payload, AggValue([value_payload_len], '{0} + 1')) + [
                If(EqualTest(header.tcp_data_state, EST), [
                    SetValue(header.tcp_data_fin_seq_1, AggValue(
                        [value_seq_num, value_payload_len], '{0} + {1}')),
                ], [
                    SetValue(header.tcp_data_fin_seq_2, value_seq_num),
                ]),
            ]),
        ]),
    ]),
    If(value_to_active,
       update_window(header.tcp_data_passive_lwnd, header.tcp_data_passive_wscale, header.tcp_data_passive_wsize, header.tcp_data_active_lwnd, header.tcp_data_active_wscale,
                     header.tcp_data_active_wsize)),
    If(value_to_passive,
       update_window(header.tcp_data_active_lwnd, header.tcp_data_active_wscale, header.tcp_data_active_wsize, header.tcp_data_passive_lwnd, header.tcp_data_passive_wscale,
                     header.tcp_data_passive_wsize)),
    Command(sequence, 'InsertMeta', [
        Value([instance_table]),
        value_seq_num,
        Value([reg_data], '{0}'),
        Value([reg_wnd, reg_wnd_size], '({0}, {0} + {1})')
    ],
        opt_target=True, aux=InsertWriter()),
    SetValue(psm_triggered, no),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.tcp_data_state, CLOSED), [
            If(AggValue([value_syn], '{0} == 0'), [
                SetValue(psm_trans, trans_fake),
                SetValue(header.tcp_data_state, TERMINATE),
                SetValue(psm_triggered, yes),
            ]),
            If(AggValue([value_syn, value_ack], '{0} == 1 and {1} == 0', AggValueWriter('{0} && !{1}')), [
                SetValue(psm_trans, trans_hs1),
                SetValue(header.tcp_data_state, SYN_SENT),
                SetValue(psm_triggered, yes),
            ]),
            to_rst(CLOSED),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.tcp_data_state, SYN_SENT), [
            If(AggValue([value_to_active, value_syn, value_ack], '{0} and {1} == 1 and {2} == 1',
                        AggValueWriter('{0} && {1} && {2}')), [
                SetValue(psm_trans, trans_hs2),
                SetValue(header.tcp_data_state, SYN_RECV),
                SetValue(psm_triggered, yes),
            ]),
            to_rst(SYN_SENT),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.tcp_data_state, SYN_RECV), [
            If(value_ack, [
                SetValue(header.tcp_data_seen_ack, yes),
            ]),
            If(EqualTest(header.tcp_data_seen_ack, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_hs3),
                    SetValue(header.tcp_data_state, EST),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(SYN_RECV),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.tcp_data_state, EST), [
            If(AggValue([value_fin], '{0} == 0'), [
                SetValue(psm_trans, trans_buffering),
                SetValue(header.tcp_data_state, EST),
                SetValue(psm_triggered, yes),
            ]),
            If(value_fin, [
                SetValue(header.tcp_data_seen_fin, yes),
            ]),
            If(EqualTest(header.tcp_data_seen_fin, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv1),
                    SetValue(header.tcp_data_state, FIN_WAIT),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(EST),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.tcp_data_state, FIN_WAIT), [
            If(AggValue([value_ack, value_fin, Value([header.tcp_data_fin_seq_1], '{}'), value_ack_num],
                        '{0} and {1} == 0 and {2} + 1 == {3}', AggValueWriter('{0} && !{1} && {2} + 1 == {3}')), [
                SetValue(header.tcp_data_wv2_expr, yes),
            ]),
            If(EqualTest(header.tcp_data_wv2_expr, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv2),
                    SetValue(header.tcp_data_state, CLOSE_WAIT),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            If(AggValue([value_ack, value_fin, Value([header.tcp_data_fin_seq_1], '{}'), value_ack_num],
                        '{0} and {1} and {2} + 1 == {3}', AggValueWriter('{0} && {1} && {2} + 1 == {3}')), [
                SetValue(header.tcp_data_wv2_fast_expr, yes),
            ]),
            If(EqualTest(header.tcp_data_wv2_fast_expr, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv2_fast),
                    SetValue(header.tcp_data_state, LAST_ACK),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(FIN_WAIT),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.tcp_data_state, CLOSE_WAIT), [
            If(value_fin, [
                SetValue(psm_trans, trans_wv3),
                SetValue(header.tcp_data_state, LAST_ACK),
                SetValue(psm_triggered, yes),
            ]),
            to_rst(CLOSE_WAIT),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(header.tcp_data_state, LAST_ACK), [
            If(AggValue([value_ack, Value([header.tcp_data_fin_seq_2], '{}'), value_ack_num], '{0} and {1} + 1 == {2}',
                        AggValueWriter('{0} && {1} + 1 == {2}')), [
                SetValue(header.tcp_data_wv4_expr, yes),
            ]),
            If(EqualTest(header.tcp_data_wv4_expr, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv4),
                    SetValue(header.tcp_data_state, TERMINATE),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(LAST_ACK),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_trans, trans_buffering), [
        Command(sequence, 'Assemble', [],
                opt_target=True, aux=SeqAssembleWriter()),
    ]),
    Command(runtime, 'Call{on_EST}', [value_payload_len, value_to_active], opt_target=True, aux=CallWriter(
        'handle_tcp_payload', [reg_data, reg_to_active, psm_trans, header.tcp_data_state])),
    If(EqualTest(header.tcp_data_state, TERMINATE), [
        Command(instance_table, 'Destroy', [],
                opt_target=True, aux=DestroyInstWriter()),
    ])
]

tcp_seq = Seq(
    Value([header.tcp_seq], 'WV_NToH32({0})'),
    Value([reg_data], '{0}'),
    False,
    Value([reg_takeup], '{0}'),
    Value([reg_wnd], '{0}'),
    Value([reg_wnd, reg_wnd_size], '{0} + {1}'),
)
