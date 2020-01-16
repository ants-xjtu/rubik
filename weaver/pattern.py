from weaver.code import Command, Choice, AggValue, Value, If
from weaver.stock.reg import sequence, instance_table, runtime
from weaver.writer import ContentWriter, CreateLightInstWriter, EmptyAlignWriter, SetContentWriter
from weaver.auxiliary import InstrAux, ValueAux


class Patterns:
    def __init__(self, seq):
        self.seq = seq

    def __call__(self, codes):
        for p in [pat1, pat2, pat3, pat4]:
            codes = p(codes, self.seq)
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


def pat1(codes, seq):
    create = find_index(codes, IsCommand(instance_table, 'Create', 1))
    insert = find_index(codes, IsCommand(sequence, 'Insert', 1))
    assemble = find_index(codes, IsCommand(sequence, 'Assemble', 1))
    if all(x is not None for x in [create, insert, assemble]) and create < insert < assemble:
        return codes[:insert] + codes[insert + 1:assemble] + [
            Command(sequence, 'SetContent', [
                    seq.data], aux=InstrAux(SetContentWriter(), 1), opt_target=True)
        ] + codes[assemble + 1:]
    return codes


def pat2(codes, seq):
    insert = find_index(codes, IsCommand(sequence, 'Insert', 2))
    assemble = find_index(codes, IsCommand(sequence, 'Assemble', 2))
    if insert is not None and assemble is not None and insert < assemble:
        return codes[:insert] + [
            Choice(AggValue([Value([sequence]), seq.offset], 'EmptyAlign(seq->offset)', aux=ValueAux(EmptyAlignWriter())), [
                Command(sequence, 'SetContent', [
                        seq.data], aux=InstrAux(SetContentWriter(), 2), opt_target=True)
            ] + codes[insert + 1:assemble] + codes[assemble + 1:], [
                Command(sequence, 'Insert', codes[insert].args, aux=InstrAux(
                    getattr(codes[insert].aux, 'writer', None) or codes[insert].aux, 2), opt_target=True),
                *codes[insert + 1:assemble],
                Command(sequence, 'Assemble', codes[assemble].args, aux=InstrAux(
                    getattr(codes[assemble].aux, 'writer', None) or codes[assemble].aux, 2), opt_target=True),
                *codes[assemble + 1:],
            ])
        ]
    return codes


def pat3(codes, seq):
    insert = find_index(codes, IsCommand(sequence, 'Insert', 3))
    assemble = find_index(codes, IsCommand(sequence, 'Assemble', 3))
    nexti = find_index(codes, IsCommand(runtime, 'Next', 3))
    call = find_index(codes, IsCommand(runtime, 'Call', 3))
    if (
        all(instr is not None for instr in [insert, assemble]) and
        all(instr is None for instr in [nexti, call]) and
        insert < assemble
    ):
        return codes[:assemble] + codes[assemble + 1:]
    return codes


def pat4(codes, seq):
    create = find_index(codes, IsCommand(instance_table, 'Create', 4))
    destroy = find_index(codes, IsCommand(instance_table, 'Destroy', 4))
    if create is not None and destroy is not None and create < destroy:
        create_light = Command(instance_table, 'CreateLight',
                               codes[create].args, aux=InstrAux(CreateLightInstWriter(), 4))
        insert = find_index(codes, IsCommand(sequence, 'Insert', 4))
        if insert is None:
            return codes[:create] + [create_light] + codes[create + 1:destroy] + codes[destroy + 1:]
        else:
            return codes[:create] + [create_light] + codes[create + 1:insert] + [
                Command(sequence, 'SetContent', [
                    seq.data], aux=InstrAux(SetContentWriter(), 1), opt_target=True)
            ] + codes[insert + 1:destroy] + codes[destroy + 1:]
    return codes
