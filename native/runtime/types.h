#ifndef WEAVER_RUNTIME_TYPES_H
#define WEAVER_RUNTIME_TYPES_H

#include <limits.h>
#include <netinet/in.h>
#include <stddef.h>
#include <stdint.h>

typedef uint8_t WV_Byte;
typedef uint8_t WV_U8;
typedef uint16_t WV_U16;
typedef uint32_t WV_U32;
typedef uint64_t WV_U64;
typedef int32_t WV_I32;
typedef double WV_F;
typedef void* WV_Any;

const static WV_U32 WV_U32_MAX = 0xffffffff;

static inline WV_U32 WV_SafeAdd32(WV_U32 a, WV_U32 b)
{
    if (WV_U32_MAX - a < b) {
        return WV_U32_MAX;
    }
    return a + b;
}

static inline WV_U16 WV_NToH16(WV_U16 x)
{
    return ntohs(x);
}

static inline WV_U32 WV_NToH32(WV_U32 x)
{
    return ntohl(x);
}

typedef struct _WV_ByteSlice {
    const WV_Byte* cursor;
    WV_U32 length;
} WV_ByteSlice;

static const WV_ByteSlice WV_EMPTY = { .cursor = NULL, .length = 0 };

static inline WV_ByteSlice WV_SliceAfter(WV_ByteSlice slice, WV_U32 index)
{
    if (slice.cursor == NULL) {
        return WV_EMPTY;
    }
    if (slice.length < index) {
        return (WV_ByteSlice){ .cursor = slice.cursor + slice.length, .length = 0 };
    }
    WV_ByteSlice after = { .cursor = slice.cursor + index, .length = slice.length - index };
    return after;
}

static inline WV_ByteSlice WV_SliceBefore(WV_ByteSlice slice, WV_U32 index)
{
    if (slice.cursor == NULL) {
        return WV_EMPTY;
    }
    if (slice.length < index) {
        return slice;
    }
    return (WV_ByteSlice){ .cursor = slice.cursor, .length = index };
}

static inline WV_U8 WV_UpdateV(WV_U8* v, WV_U8 expr)
{
    if (expr) {
        *v = 1;
    }
    return *v;
}

#endif