#ifndef WEAVER_RUNTIME_SLICE_H
#define WEAVER_RUNTIME_SLICE_H

#include "types.h"

typedef struct _WV_ByteSlice {
    const WV_Byte *cursor;
    WV_U32 length;
} WV_ByteSlice;

static inline WV_ByteSlice WV_SliceAfter(WV_ByteSlice slice, WV_U32 index) {
    WV_ByteSlice after = { .cursor = slice.cursor + index, .length = slice.length - index };
    return after;
}

#endif