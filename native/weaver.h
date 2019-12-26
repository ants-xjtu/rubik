// Weaver Runtime Header
#ifndef WV_WEAVER_H
#define WV_WEAVER_H

#include <stdint.h>
#include "runtime/tommyds/tommyhashdyn.h"

typedef uint8_t WV_Byte;
typedef uint8_t WV_U8;
typedef uint16_t WV_U16;
typedef uint32_t WV_U32;
typedef uint64_t WV_U64;
typedef struct WV_ByteSlice {
    WV_Byte *cursor;
    WV_U32 length;
} WV_ByteSlice;

typedef tommy_hashdyn WV_Table;

typedef struct WV_Runtime {
    WV_Table *tables;
} WV_Runtime;

extern WV_U8 WV_CONFIG_TABLE_COUNT;

WV_U8 WV_ProcessPacket(WV_ByteSlice, WV_Runtime *);

WV_U8 WV_InitRuntime(WV_Runtime *);

#endif