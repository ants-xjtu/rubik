from weaver.code import Command, Choice, AggValue, Value, If
from weaver.writer import ContentWriter, CreateLightInstWriter, EmptyAlignWriter, SetContentWriter, InsertWriter
from weaver.auxiliary import InstrAux, ValueAux, sequence, instance as instance_table, runtime


class Patterns:
    def __init__(self, seq):
        self.seq = seq

    def __call__(self, codes):
        for i, p in enumerate([pat4, pat2, pat3]):
            codes = p(codes, self.seq, i)
        return codes


class IsCommand:
    def __init__(self, provider, name, stage):
        self.provider = provider
        self.name = name
        self.stage = stage

    def __call__(self, instr):
        # backward cap
        if not hasattr(instr.aux, 'opt_stage'):
            opt_stage = -1
        else:
            opt_stage = instr.aux.opt_stage
        return (
            isinstance(instr, Command) and
            instr.provider == self.provider and
            instr.name == self.name and
            opt_stage < self.stage
        )


def find_index(codes, is_command):
    return next((i for i, instr in enumerate(codes) if is_command(instr)), None)


# def pat1(codes, seq):
#     create = find_index(codes, IsCommand(instance_table, 'Create', 1))
#     insert = find_index(codes, IsCommand(sequence, 'Insert', 1))
#     assemble = find_index(codes, IsCommand(sequence, 'Assemble', 1))
#     if all(x is not None for x in [create, insert, assemble]) and create < insert < assemble:
#         return codes[:insert] + codes[insert + 1:assemble] + [
#             Command(sequence, 'SetContent', [
#                     seq.data], aux=InstrAux(SetContentWriter(), 1), opt_target=True)
#         ] + codes[assemble + 1:]
#     return codes


def pat2(codes, seq, stage):
    insert = find_index(codes, IsCommand(sequence, 'Insert', stage))
    assemble = find_index(codes, IsCommand(sequence, 'Assemble', stage))
    if insert is not None and assemble is not None and insert < assemble:
        return codes[:insert] + [
            Choice(AggValue([Value([sequence, instance_table]), seq.offset, seq.data, seq.takeup], 'EmptyAlign(seq->offset)', aux=ValueAux(EmptyAlignWriter())), [
                Command(sequence, 'Insert', codes[insert].args, aux=InstrAux(InsertWriter(True), stage), opt_target=True),
                *codes[insert + 1:assemble],
                Command(sequence, 'Assemble', codes[assemble].args, aux=InstrAux(
                    getattr(codes[assemble].aux, 'writer', None) or codes[assemble].aux, stage), opt_target=True),
                Command(sequence, 'SetContent', [
                        seq.data], aux=InstrAux(SetContentWriter(), stage), opt_target=True),
                *codes[assemble + 1:],
            ], [
                Command(sequence, 'Insert', codes[insert].args, aux=InstrAux(InsertWriter(), stage), opt_target=True),
                *codes[insert + 1:assemble],
                Command(sequence, 'Assemble', codes[assemble].args, aux=InstrAux(
                    getattr(codes[assemble].aux, 'writer', None) or codes[assemble].aux, stage), opt_target=True),
                *codes[assemble + 1:],
            ])
        ]
    return codes


def pat3(codes, seq, stage):
    insert = find_index(codes, IsCommand(sequence, 'Insert', stage))
    assemble = find_index(codes, IsCommand(sequence, 'Assemble', stage))
    nexti = find_index(codes, IsCommand(runtime, 'Next', stage))
    call = find_index(codes, IsCommand(runtime, 'Call', stage))
    if (
        all(instr is not None for instr in [insert, assemble]) and
        all(instr is None for instr in [nexti, call]) and
        insert < assemble
    ):
        return codes[:assemble] + codes[assemble + 1:]
    return codes


def pat4(codes, seq, stage):
    create = find_index(codes, IsCommand(instance_table, 'Create', stage))
    destroy = find_index(codes, IsCommand(instance_table, 'Destroy', stage))
    if create is not None and destroy is not None and create < destroy:
        create_light = Command(instance_table, 'CreateLight',
                               codes[create].args, aux=InstrAux(CreateLightInstWriter(), stage))
        insert = find_index(codes, IsCommand(sequence, 'Insert', stage))
        assemble = find_index(codes, IsCommand(sequence, 'Assemble', stage))
        if assemble is not  None:
            assert insert is not None
            return codes[:create] + [create_light] + codes[create + 1:insert] + codes[insert + 1:assemble] + [
                Command(sequence, 'SetContent', [
                    seq.data], aux=InstrAux(SetContentWriter(), stage), opt_target=True)
            ] + codes[assemble + 1:destroy] + codes[destroy + 1:]
        elif insert is not None:
            return codes[:create] + [create_light] + codes[create + 1:insert] + codes[insert + 1:destroy] + codes[destroy + 1:]
    return codes
