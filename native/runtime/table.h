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
    tommy_hashdyn tommy;
    // TODO: pre-alloc instance pool
} WV_Table;

#define WV_INST_EXTRA_DECL(key_size) \
    WV_Byte key[(key_size)]; \
    WV_U32 seq; \
    tommy_node node;

#define WV_InstHeader(key_size) \
    struct { \
        WV_INST_EXTRA_DECL(key_size) \
    }

static int is_equal(const void *key_any, const void *inst) {
    const WV_ByteSlice *key = key_any;
    return memcmp(key->cursor, inst, key->length);
}

#if TOMMY_SIZE_BIT == 32
#define tommy_hash tommy_hash_u32
#else
#define tommy_hash tommy_hash_u64
#endif

static inline WV_U8 WV_InitTable(WV_Table *table, WV_U32 layer_id) {
    tommy_hashdyn_init(&table->tommy);
    //
    return 0;
}

static inline WV_U8 WV_CleanTable(WV_Table *table) {
    tommy_hashdyn_foreach(&table->tommy, free);
    tommy_hashdyn_done(&table->tommy);
    return 0;
}

static inline WV_Any WV_FetchInst(WV_Table *table, WV_ByteSlice key) {
    return tommy_hashdyn_search(&table->tommy, is_equal, &key, tommy_hash(0, key.cursor, (tommy_size_t)key.length));
}

static inline WV_Any WV_CreateInst(WV_Table *table, WV_ByteSlice key, WV_U32 inst_size) {
    WV_InstHeader(key.length) *inst = malloc(sizeof(WV_Byte) * inst_size);
    memcpy(&inst->key, key.cursor, key.length);
    tommy_hashdyn_insert(&table->tommy, &inst->node, inst, tommy_hash(0, key.cursor, (tommy_size_t)key.length));
    return inst;
}

static inline WV_U8 WV_DestroyInst(WV_Table *table, WV_ByteSlice key) {
    WV_Byte *inst = tommy_hashdyn_remove(&table->tommy, is_equal, &key, tommy_hash(0, key.cursor, (tommy_size_t)key.length));
    if (inst) {
        free(inst);
        return 0;
    }
    return 1;
}

#define WV_BI_INST_EXTRA_DECL(key_size) \
    WV_Byte key1[(key_size)]; \
    WV_U8 reverse1; \
    WV_U32 seq1; \
    tommy_node node1; \
    WV_Byte key2[(key_size)]; \
    WV_U8 reverse2; \
    WV_U32 seq2; \
    tommy_node node2; \

#define WV_BiInstHeader(key_size) \
    struct { \
        WV_Byte key[(key_size)]; \
        WV_U8 reverse; \
        WV_U32 seq; \
        tommy_node node; \
    }

static inline WV_Any WV_CreateBiInst(WV_Table *table, WV_ByteSlice half_key1, WV_ByteSlice half_key2, WV_U32 inst_size) {
    tommy_size_t key_length = (tommy_size_t)(half_key1.length + half_key2.length);
    WV_BiInstHeader(key_length) *this_header = malloc(sizeof(WV_Byte) * inst_size);
    memcpy(&this_header->key, half_key1.cursor, half_key1.length);
    memcpy(&this_header->key[half_key1.length], half_key2.cursor, half_key2.length);
    this_header->reverse = 0;
    WV_BiInstHeader(key_length) *that_header = (WV_Any)((WV_Byte *)this_header + sizeof(WV_BiInstHeader(key_length)));
    memcpy(&that_header->key, half_key2.cursor, half_key2.length);
    memcpy(&that_header->key[half_key2.length], half_key1.cursor, half_key1.length);
    that_header->reverse = 1;
    tommy_hashdyn_insert(&table->tommy, &this_header->node, this_header, tommy_hash(0, &this_header->key, key_length));
    tommy_hashdyn_insert(&table->tommy, &that_header->node, that_header, tommy_hash(0, &that_header->key, key_length));
    return this_header;
}

static inline WV_Any WV_InstData(WV_Any inst_header, WV_U32 key_length) {
    return ((WV_BiInstHeader(key_length) *)inst_header)->reverse ? (WV_Byte *)inst_header - sizeof(WV_BiInstHeader(key_length)) : inst_header;
}

static inline WV_U8 WV_DestroyBiInst(WV_Table *table, WV_ByteSlice this_key) {
    WV_ByteSlice that_key;
    tommy_size_t key_length = (tommy_size_t)this_key.length;
    WV_BiInstHeader(key_length) *that_header;
    WV_BiInstHeader(key_length) *this_header =
        tommy_hashdyn_remove(&table->tommy, is_equal, &this_key, tommy_hash(0, this_key.cursor, key_length));
    if (!this_header) {
        return 1;
    }
    if (this_header->reverse) {
        that_header = (WV_Any)((WV_Byte *)this_header - sizeof(WV_BiInstHeader(key_length)));
    } else {
        that_header = (WV_Any)((WV_Byte *)this_header + sizeof(WV_BiInstHeader(key_length)));
    }
    that_key = (WV_ByteSlice){ .cursor = that_header->key, .length = key_length};
    if (!tommy_hashdyn_remove(&table->tommy, is_equal, &that_key, tommy_hash(0, that_key.cursor, key_length))) {
        return 1;
    }
    free(this_header->reverse ? (WV_Any)that_header : (WV_Any)this_header);
    return 0;
}

static void free_bi_inst(void *key_length, void *inst) {
    WV_BiInstHeader(*(WV_U32 *)key_length) *header = inst;
    if (!header->reverse) {
        free(inst);
    }
}

static inline WV_U8 WV_CleanBiTable(WV_Table *table, WV_U32 key_length) {
    tommy_hashdyn_foreach_arg(&table->tommy, free_bi_inst, &key_length);
    tommy_hashdyn_done(&table->tommy);
    return 0;
}

#endif