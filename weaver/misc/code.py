from weaver.code import If, SetValue, Command, AggValue, Value, EqualTest

# system:
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

saddr = Value([header_parser], 'header->saddr')
daddr = Value([header_parser], 'header->daddr')
DUMP = Value([], '0');
FRAG = Value([], '1')
dump = Value([], '0');
frag = Value([], '1');
last = Value([], '2');
more = Value([], '3')
dont_frag = Value([header_parser], 'header->dont_frag')
more_frag = Value([header_parser], 'header->more_frag')
ip = [
    If(AggValue([Value([instance_table]), saddr, daddr], 'InstExist({1}, {2})'), [
        Command(instance_table, 'Fetch', [saddr, daddr]),
        SetValue(psm_state, Value([instance_table], 'inst->state')),
        SetValue(1003, Value([instance_table], 'inst->seen_dont_frag')),
    ], [
           Command(instance_table, 'Create', [saddr, daddr]),
           SetValue(psm_state, no),
           SetValue(1003, no),
       ]),
    Command(sequence, 'InsertMeta',
            [Value([header_parser], 'header->offset'), Value([header_parser], 'header_meta->payload_length')]),
    Command(sequence, 'InsertData', [Value([header_parser], 'header_meta->payload')]),
    SetValue(psm_triggered, no),
    If(EqualTest(psm_triggered, no), [
        If(EqualTest(psm_state, DUMP), [
            If(dont_frag, [
                SetValue(psm_trans, dump),
                SetValue(psm_triggered, yes),
            ]),
            If(more_frag, [
                SetValue(psm_trans, more),
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
                If(Value([sequence], 'SeqReady()'), [
                    SetValue(psm_trans, last),
                    SetValue(psm_triggered, yes),
                ]),
            ]),
            If(AggValue([EqualTest(1003, no), Value([sequence], '!SeqReady()')], '{0} || {1}'), [
                SetValue(psm_trans, frag),
                SetValue(psm_triggered, yes),
            ]),
            SetValue(psm_triggered, yes),
        ]),
    ]),
    If(EqualTest(psm_state, DUMP), [
        Command(sequence, 'Assemble', []),
    ]),
    If(EqualTest(psm_state, DUMP), [
        If(AggValue([Value([header_parser], 'header->protocol'), Value([], '42')], '{0} == {1}'), [
            Command(0, 'Next', []),
            Command(instance_table, 'Destroy', []),
        ])
    ])
]
