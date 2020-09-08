#ifndef WEAVER_RUNTIME_SEQ_NEXT_H
#define WEAVER_RUNTIME_SEQ_NEXT_H

#include "malloc.h"
#include "types.h"

#define WV_CONFIG_SeqNodeCount 32
#define WV_CONFIG_SeqBufferSize (8 * (1 << 10))

typedef struct {
  WV_U32 left, right;
} _Part;

typedef struct {
  WV_U32 offset;
  _Part parts[WV_CONFIG_SeqNodeCount];
  WV_U8 part_count;
} ZeroBasedSeq;

WV_U8 InitSeqZD(ZeroBasedSeq *seq) {
  seq->offset = 0;
  seq->part_count = 0;
}

#endif