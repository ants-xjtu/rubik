#ifndef WEAVER_RUNTIME_TYPES_H
#define WEAVER_RUNTIME_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <limits.h>
#include <netinet/in.h>

typedef uint8_t WV_Byte;
typedef uint8_t WV_U8;
typedef uint16_t WV_U16;
typedef uint32_t WV_U32;
typedef uint64_t WV_U64;
typedef int32_t WV_I32;
typedef double WV_F;
typedef void *WV_Any;
const static WV_U32 WV_U32_MAX = 0xffffffff;

static inline WV_U16 WV_NToH16(WV_U16 x) {
    return ntohs(x);
}
static inline WV_U32 WV_NToH32(WV_U32 x) {
    return ntohl(x);
}

typedef struct _WV_ByteSlice {
    const WV_Byte *cursor;
    WV_U32 length;
} WV_ByteSlice;

static const WV_ByteSlice WV_EMPTY = { .cursor = NULL, .length = 0 };

static inline WV_ByteSlice WV_SliceAfter(WV_ByteSlice slice, WV_U32 index) {
    if (slice.cursor == NULL) {
        return WV_EMPTY;
    }
    WV_ByteSlice after = { .cursor = slice.cursor + index, .length = slice.length - index };
    return after;
}

static inline WV_ByteSlice WV_SliceBefore(WV_ByteSlice slice, WV_U32 index) {
    if (slice.cursor == NULL) {
        return WV_EMPTY;
    }
    return (WV_ByteSlice){ .cursor = slice.cursor, .length = index };
}

#endif