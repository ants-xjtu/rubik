#ifndef WEAVER_RUNTIME_SEQ_H
#define WEAVER_RUNTIME_SEQ_H

#include "types.h"

typedef struct {
    //
} WV_Seq;

static inline WV_U8 WV_InsertMeta(WV_Seq *seq, WV_U32 offset, WV_ByteSlice data) {
    //
    return 0;
}

static inline WV_U8 WV_InsertData(WV_Seq *seq, WV_ByteSlice data) {
    //
    return 0;
}

static inline WV_U8 WV_SeqReady(WV_Seq *seq) {
    //
    return 0;
}

static inline WV_ByteSlice WV_SeqAssemble(WV_Seq *seq) {
    //
    return (WV_ByteSlice){ .cursor = NULL, .length = 0 };
}

#endif