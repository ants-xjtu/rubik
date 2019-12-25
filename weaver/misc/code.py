from weaver.code import *
from typing import List

# system:
runtime = 0
header_parser = 100
instance_table = 101
sequence = 102
# common:
psm_state = 1000
psm_triggered = 1001
psm_trans = 1002

yes = Value([], '1')
no = Value([], '0')
ready = Value([sequence], 'seq->ready')

# IP protocol
saddr = Value([header_parser], 'header->saddr')
daddr = Value([header_parser], 'header->daddr')
DUMP = Value([], '0')
FRAG = Value([], '1')
dump = Value([], '0')
frag = Value([], '1')
last = Value([], '2')
more = Value([], '3')
dont_frag = Value([header_parser], 'header->dont_frag')
more_frag = Value([header_parser], 'header->more_frag')
ip = [
    If(AggValue([Value([instance_table]), saddr, daddr], 'InstExist({1}, {2})'), [
        Command(instance_table, 'Fetch', [saddr, daddr]),
        SetValue(psm_state, Value([instance_table], 'inst->state')),
        SetValue(1003, Value([instance_table], 'inst->seen_dont_frag')),
    ], [
           Command(instance_table, 'Create', [saddr, daddr], opt_target=True),
           SetValue(psm_state, DUMP),
           SetValue(1003, no),
       ]),
    Command(sequence, 'InsertMeta',
            [Value([instance_table]), Value([header_parser], 'header->offset'),
             Value([header_parser], 'header_meta->payload_length')],
            opt_target=True),
    Command(sequence, 'InsertData', [Value([instance_table]), Value([header_parser], 'header_meta->payload')],
            opt_target=True),
    SetValue(psm_triggered, no),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, DUMP), [
            If(dont_frag, [
                SetValue(psm_trans, dump),
                SetValue(psm_state, DUMP),
                SetValue(psm_triggered, yes),
            ]),
            If(more_frag, [
                SetValue(psm_trans, more),
                SetValue(psm_state, FRAG),
                SetValue(psm_triggered, yes),
            ]),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, FRAG), [
            If(dont_frag, [
                SetValue(1003, yes),
            ]),
            If(EqualTest(1003, yes), [
                If(ready, [
                    SetValue(psm_trans, last),
                    SetValue(psm_state, DUMP),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            If(AggValue([EqualTest(1003, no), Value([sequence], '!SeqReady()')], '{0} || {1}'), [
                SetValue(psm_trans, frag),
                SetValue(psm_state, FRAG),
                SetValue(psm_triggered, yes),
            ]),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_state, DUMP), [
        Command(sequence, 'Assemble', [], opt_target=True),
    ]),
    Command(instance_table, 'Set{state}', [Value([psm_state], '{0}')]),
    Command(instance_table, 'Set{seen_dont_frag}', [Value([1003], '{0}')]),
    If(EqualTest(psm_state, DUMP), [
        If(AggValue([Value([header_parser], 'header->protocol'), Value([], '42')], '{0} == {1}'), [
            Command(runtime, 'Next', [], opt_target=True),
            Command(instance_table, 'Destroy', [], opt_target=True),
        ])
    ])
]

# TCP protocol
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

reg_data_len = 1003
reg_data = 1004
reg_fin_seq_1 = 1005
reg_fin_seq_2 = 1006
reg_passive_lwnd = 1007
reg_passive_wscale = 1008
reg_passive_wsize = 1009
reg_active_lwnd = 1010
reg_active_wscale = 1011
reg_active_wsize = 1012
reg_seen_ack = 1013
reg_seen_fin = 1014
reg_wv2_expr = 1015
reg_wv2_fast_expr = 1016
reg_wv4_expr = 1017
reg_wnd = 2000
reg_wnd_size = 2001
reg_to_active = 2002
value_payload = Value([header_parser], 'header_meta->payload')
value_payload_len = Value([header_parser], 'header_meta->payload_length')
value_seq_num = Value([header_parser], 'header->seq_num')
value_ack = Value([header_parser], 'header->ack')
value_ack_num = Value([header_parser], 'header->ack_num')
value_syn = Value([header_parser], 'header->syn')
value_fin = Value([header_parser], 'header->fin')
value_to_active = Value([reg_to_active], '{0}')
value_to_passive = Value([reg_to_active], 'not {0}')


def assign_data(data: Value, data_len: Value) -> List[Instr]:
    return [
        SetValue(reg_data, data),
        SetValue(reg_data_len, data_len),
    ]


def update_window(that_lwnd: int, that_wscale: int, that_wsize: int, this_lwnd: int, this_wscale: int,
                  this_wsize: int) -> List[Instr]:
    return [
        If(Value([header_parser], 'HeaderContain(tcp_ws)'), [
            SetValue(that_wscale, Value([header_parser], 'header->ws_value')),
        ]),
        SetValue(that_wsize, Value([header_parser], 'header->window_size')),
        SetValue(that_lwnd, Value([header_parser], 'header->ack_num')),
        SetValue(reg_wnd, Value([this_lwnd], '{0}')),
        SetValue(reg_wnd_size, Value([this_wsize, this_wscale], '{0} << {1}')),
    ]


def to_rst(from_state: Value):
    to_state = AggValue([from_state], f'{{0}} + {TERMINATE}')
    trans = AggValue([from_state], f'{{0}} + {trans_wv4}')
    return If(Value([header_parser], 'header->rst'), [
        SetValue(psm_trans, trans),
        SetValue(psm_state, to_state),
        SetValue(psm_triggered, yes),
    ])


tcp = [
    If(AggValue([Value([instance_table]), saddr, sport, daddr, dport], 'InstExist({1}, {2}, {3}, {4})'), [
        Command(instance_table, 'Fetch', [saddr, sport, daddr, dport]),
        SetValue(reg_to_active, Value([instance_table], 'InstToActive()')),
        SetValue(psm_state, Value([instance_table], 'inst->state')),
        SetValue(reg_fin_seq_1, Value([instance_table], 'inst->reg_fin_seq_1')),
        SetValue(reg_fin_seq_2, Value([instance_table], 'inst->reg_fin_seq_2')),
        SetValue(reg_active_wsize, Value([instance_table], 'inst->reg_active_wsize')),
        SetValue(reg_active_wscale, Value([instance_table], 'inst->reg_active_wscale')),
        SetValue(reg_active_lwnd, Value([instance_table], 'inst->reg_active_lwnd')),
        SetValue(reg_passive_wsize, Value([instance_table], 'inst->reg_passive_wsize')),
        SetValue(reg_passive_wscale, Value([instance_table], 'inst->reg_passive_wscale')),
        SetValue(reg_passive_lwnd, Value([instance_table], 'inst->reg_passive_lwnd')),
        SetValue(reg_seen_ack, Value([instance_table], 'inst->reg_seen_ack')),
        SetValue(reg_seen_fin, Value([instance_table], 'inst->reg_seen_fin')),
        SetValue(reg_wv2_expr, Value([instance_table], 'inst->reg_wv2_expr')),
        SetValue(reg_wv2_fast_expr, Value([instance_table], 'inst->reg_wv2_fast_expr')),
        SetValue(reg_wv4_expr, Value([instance_table], 'inst->reg_wv4_expr')),
    ], [
           Command(instance_table, 'Create', [saddr, sport, daddr, dport], opt_target=True),
           SetValue(reg_to_active, no),
           SetValue(psm_state, CLOSED),
           SetValue(reg_fin_seq_1, no),
           SetValue(reg_fin_seq_2, no),
           SetValue(reg_active_wsize, Value([], '(1 << 32) - 1')),
           SetValue(reg_active_wscale, no),
           SetValue(reg_active_lwnd, no),
           SetValue(reg_passive_wsize, Value([], '(1 << 32) - 1')),
           SetValue(reg_passive_wscale, no),
           SetValue(reg_passive_lwnd, no),
           SetValue(reg_seen_ack, no),
           SetValue(reg_seen_fin, no),
           SetValue(reg_wv2_expr, no),
           SetValue(reg_wv2_fast_expr, no),
           SetValue(reg_wv4_expr, no),
       ]),
    If(value_ack, assign_data(value_payload, value_payload_len), [
        If(value_syn, assign_data(no, Value([], '1')), [
            If(value_fin, assign_data(value_payload, AggValue([value_payload_len], '{0} + 1')) + [
                If(EqualTest(psm_state, EST), [
                    SetValue(reg_fin_seq_1, AggValue([value_seq_num, value_payload_len], '{0} + {1}')),
                ], [
                       SetValue(reg_fin_seq_2, value_seq_num),
                   ]),
            ]),
        ]),
    ]),
    If(value_to_active,
       update_window(reg_passive_lwnd, reg_passive_wscale, reg_passive_wsize, reg_active_lwnd, reg_active_wscale,
                     reg_active_wsize)),
    If(value_to_passive,
       update_window(reg_active_lwnd, reg_active_wscale, reg_active_wsize, reg_passive_lwnd, reg_passive_wscale,
                     reg_passive_wsize)),
    Command(sequence, 'InsertMeta',
            [Value([instance_table]), value_seq_num, Value([reg_data_len], '{0}'),
             Value([reg_wnd, reg_wnd_size], '({0}, {0} + {1})')],
            opt_target=True),
    Command(sequence, 'InsertData', [Value([instance_table]), Value([reg_data], '{0}')], opt_target=True),
    SetValue(psm_triggered, no),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, CLOSED), [
            If(AggValue([value_syn], '{0} == 0'), [
                SetValue(psm_trans, trans_fake),
                SetValue(psm_state, TERMINATE),
                SetValue(psm_triggered, yes),
            ]),
            If(AggValue([value_syn, value_ack], '{0} == 1 && {1} == 0'), [
                SetValue(psm_trans, trans_hs1),
                SetValue(psm_state, SYN_SENT),
                SetValue(psm_triggered, yes),
            ]),
            to_rst(CLOSED),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, SYN_SENT), [
            If(AggValue([value_to_active, value_syn, value_ack], '{0} && {1} == 1 && {2} == 1'), [
                SetValue(psm_trans, trans_hs2),
                SetValue(psm_state, SYN_RECV),
                SetValue(psm_triggered, yes),
            ]),
            to_rst(SYN_SENT),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, SYN_RECV), [
            If(value_ack, [
                SetValue(reg_seen_ack, yes),
            ]),
            If(EqualTest(reg_seen_ack, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_hs3),
                    SetValue(psm_state, EST),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(SYN_RECV),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, EST), [
            If(AggValue([value_fin], '{0} == 0'), [
                SetValue(psm_trans, trans_buffering),
                SetValue(psm_state, EST),
                SetValue(psm_triggered, yes),
            ]),
            If(value_fin, [
                SetValue(reg_seen_fin, yes),
            ]),
            If(EqualTest(reg_seen_fin, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv1),
                    SetValue(psm_state, FIN_WAIT),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(EST),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, FIN_WAIT), [
            If(AggValue([value_ack, value_fin, Value([reg_fin_seq_1], '{}'), value_ack_num],
                        '{0} && {1} == 0 && {2} + 1 == {3}'), [
                   SetValue(reg_wv2_expr, yes),
               ]),
            If(EqualTest(reg_wv2_expr, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv2),
                    SetValue(psm_state, CLOSE_WAIT),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            If(AggValue([value_ack, value_fin, Value([reg_fin_seq_1], '{}'), value_ack_num],
                        '{0} && {1} && {2} + 1 == {3}'), [
                   SetValue(reg_wv2_fast_expr, yes),
               ]),
            If(EqualTest(reg_wv2_fast_expr, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv2_fast),
                    SetValue(psm_state, LAST_ACK),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(FIN_WAIT),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, CLOSE_WAIT), [
            If(value_fin, [
                SetValue(psm_trans, trans_wv3),
                SetValue(psm_state, LAST_ACK),
                SetValue(psm_triggered, yes),
            ]),
            to_rst(CLOSE_WAIT),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, LAST_ACK), [
            If(AggValue([value_ack, Value([reg_fin_seq_2], '{}'), value_ack_num], '{0} && {1} + 1 == {2}'), [
                SetValue(reg_wv4_expr, yes),
            ]),
            If(EqualTest(reg_wv4_expr, yes), [
                If(ready, [
                    SetValue(psm_trans, trans_wv4),
                    SetValue(psm_state, TERMINATE),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            to_rst(LAST_ACK),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_trans, trans_buffering), [
        Command(sequence, 'Assemble', [], opt_target=True),
    ]),
    # there is (probably) no next layer, so let's fake a custom event
    If(EqualTest(psm_state, EST), [
        Command(runtime, 'Call{on_EST}', [value_payload_len], opt_target=True),
    ]),
    Command(instance_table, 'Set{state}', [Value([psm_state], '{0}')]),
    Command(instance_table, 'Set{reg_data_len}', [Value([reg_data_len], '{0}')]),
    Command(instance_table, 'Set{reg_data}', [Value([reg_data], '{0}')]),
    Command(instance_table, 'Set{reg_fin_seq_1}', [Value([reg_fin_seq_1], '{0}')]),
    Command(instance_table, 'Set{reg_fin_seq_2}', [Value([reg_fin_seq_2], '{0}')]),
    Command(instance_table, 'Set{reg_passive_lwnd}', [Value([reg_passive_lwnd], '{0}')]),
    Command(instance_table, 'Set{reg_passive_wscale}', [Value([reg_passive_wscale], '{0}')]),
    Command(instance_table, 'Set{reg_passive_wsize}', [Value([reg_passive_wsize], '{0}')]),
    Command(instance_table, 'Set{reg_active_lwnd}', [Value([reg_active_lwnd], '{0}')]),
    Command(instance_table, 'Set{reg_active_wscale}', [Value([reg_active_wscale], '{0}')]),
    Command(instance_table, 'Set{reg_active_wsize}', [Value([reg_active_wsize], '{0}')]),
    Command(instance_table, 'Set{reg_seen_ack}', [Value([reg_seen_ack], '{0}')]),
    Command(instance_table, 'Set{reg_seen_fin}', [Value([reg_seen_fin], '{0}')]),
    Command(instance_table, 'Set{reg_wv2_expr}', [Value([reg_wv2_expr], '{0}')]),
    Command(instance_table, 'Set{reg_wv2_fast_expr}', [Value([reg_wv2_fast_expr], '{0}')]),
    Command(instance_table, 'Set{reg_wv4_expr}', [Value([reg_wv4_expr], '{0}')]),
    If(EqualTest(psm_state, TERMINATE), [
        Command(instance_table, 'Destroy', [], opt_target=True),
    ])
]
