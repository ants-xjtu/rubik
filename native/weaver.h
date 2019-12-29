// Weaver Runtime Header
#ifndef WV_WEAVER_H
#define WV_WEAVER_H

#include <stdint.h>
#include <netinet/in.h>
#include "runtime/tommyds/tommyhashdyn.h"

typedef uint8_t WV_Byte;
typedef uint8_t WV_U8;
typedef uint16_t WV_U16;
typedef uint32_t WV_U32;
typedef uint64_t WV_U64;
typedef double WV_F;

typedef struct _WV_ByteSlice {
    const WV_Byte *cursor;
    WV_U32 length;
} WV_ByteSlice;

typedef tommy_hashdyn WV_Table;

typedef struct _WV_Profile {
    WV_U64 interval_byte_count;
    WV_U32 next_checkpoint_sec;
    WV_F last_record_sec;
    WV_F last_10_throughput[10];
    WV_F record_count;
} WV_Profile;

typedef struct _WV_Runtime {
    WV_Table *tables;
    WV_Profile profile;
} WV_Runtime;

extern WV_U8 WV_CONFIG_TABLE_COUNT;

WV_U8 WV_ProcessPacket(WV_ByteSlice, WV_Runtime *);

WV_U8 WV_InitRuntime(WV_Runtime *);

WV_U8 WV_CleanRuntime(WV_Runtime *);

WV_U8 WV_ProfileStart(WV_Runtime *);

WV_U8 WV_ProfileRecord(WV_Runtime *, WV_U32, WV_U8);

static inline WV_U16 WV_HToN16(WV_U16 x) {
    return htons(x);
}

static inline WV_U32 WV_HToN32(WV_U32 x) {
    return htonl(x);
}

static inline WV_ByteSlice WV_SliceAfter(WV_ByteSlice slice, WV_U32 index) {
    WV_ByteSlice after = { .cursor = slice.cursor + index, .length = slice.length - index };
    return after;
}

#endif