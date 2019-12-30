#ifndef WEAVER_RUNTIME_INST_H
#define WEAVER_RUNTIME_INST_H

#include "types.h"
#include "slice.h"
#include "tommyds/tommyhashdyn.h"
#include <string.h>
#include <stdlib.h>

extern WV_U8 WV_CONFIG_TABLE_COUNT;
extern WV_U32 WV_CONFIG_TABLE_INST_SIZE[];

typedef struct {
    tommy_hashdyn *tommy;
    // TODO: pre-alloc instance pool
} WV_Table;

#define WV_INST_EXTRA_DECL \
    WV_Byte **key; \
    tommy_node node;

static int is_equal(const void *key_slice, const void *inst) {
    return memcmp(((WV_ByteSlice *)key_slice)->cursor, *(WV_Byte **)inst, ((WV_ByteSlice *)key_slice)->length);
}

#if TOMMY_SIZE_BIT == 32
#define tommy_hash tommy_hash_u32
#else
#define tommy_hash tommy_hash_u64
#endif

static inline WV_U8 WV_InitTable(WV_Table *table, WV_U32 layer_id) {
    tommy_hashdyn_init(table->tommy);
    //
    return 0;
}

static inline WV_U8 WV_CleanTable(WV_Table *table) {
    tommy_hashdyn_foreach(table->tommy, free);
    tommy_hashdyn_done(table->tommy);
    return 0;
}

static inline WV_Any WV_PrefetchInst(WV_Table *table, WV_ByteSlice key) {
    return tommy_hashdyn_search(table->tommy, is_equal, &key, tommy_hash(0, key.cursor, (tommy_size_t)key.length));
}

static inline WV_Any WV_CreateInst(WV_Table *table, WV_ByteSlice key, WV_U32 inst_size) {
    WV_Byte *inst = malloc(sizeof(WV_Byte) * (inst_size + key.length));
    memcpy(inst + inst_size, key.cursor, key.length);
    *(WV_Byte **)inst = inst + inst_size;
    tommy_hashdyn_insert(table->tommy, (tommy_node *)(inst + sizeof(WV_Byte **)), inst, tommy_hash(0, key.cursor, (tommy_size_t)key.length));
}

static inline WV_U8 WV_DestroyInst(WV_Table *table, WV_ByteSlice key) {
    WV_Byte *inst = tommy_hashdyn_remove(table->tommy, is_equal, &key, tommy_hash(0, key.cursor, (tommy_size_t)key.length));
    if (inst) {
        free(inst);
        return 0;
    }
    return 1;
}

#endif