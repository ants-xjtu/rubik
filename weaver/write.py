from weaver.c import C, FuncInfo
from weaver.header import Struct


def write(recurse, layer_id, next_table, data_struct = None, bi = False):
    c = C()
    c.includes.add('"tommyds/tommyhashdyn.h"')
    if data_struct is not None:
        eq_func = f'l{layer_id}_eq'
        c.func_impls[eq_func] = FuncInfo(eq_func, [
            'const void *key', 
            'const void *inst'
        ], 'int', [
            f'return memcpy(key, inst, sizeof(H{data_struct.struct_id}_Key));'
        ])
    return c
