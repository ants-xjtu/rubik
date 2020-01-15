#ifndef WEAVER_RUNTIME_SEQ_H
#define WEAVER_RUNTIME_SEQ_H

#include "types.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

#define WV_CONFIG_SeqNodeCount 3
#define WV_CONFIG_SeqBufferSize (8 * (1 << 10))

typedef struct
{
  WV_U32 left;
  WV_U32 right;
} WV_SeqMeta;

typedef struct
{
  WV_Byte *buffer;
  WV_U32 offset;
  WV_U8 set_offset;
  WV_SeqMeta nodes[WV_CONFIG_SeqNodeCount], prefix, postfix;
  WV_U8 used_count;
  WV_U8 has_pre, has_post;
} WV_Seq;

static inline WV_U8 WV_InitSeq(WV_Seq *seq, WV_U8 use_data, WV_U32 zero_base)
{
  if (use_data)
  {
    seq->buffer = malloc(sizeof(WV_Byte) * WV_CONFIG_SeqBufferSize);
  }
  else
  {
    seq->buffer = NULL;
  }
  seq->offset = 0;
  seq->set_offset = !zero_base;
  seq->used_count = 0;
  seq->prefix = seq->postfix = (WV_SeqMeta){ .left = 0, .right = 0 };
  seq->has_pre = seq->has_post = 0;
  return 0;
}

static inline WV_U8 WV_CleanSeq(WV_Seq *seq, WV_U8 use_data)
{
  if (use_data)
  {
    free(seq->buffer);
  }
  return 0;
}

static inline WV_U8 WV_SeqEmptyAlign(WV_Seq *seq, WV_U32 offset)
{
  return seq->used_count == 0 && seq->offset == offset;
}

static inline WV_U8 WV_Insert(
    WV_Seq *seq,
    WV_U32 offset,        // offset position of data
    WV_ByteSlice data,    // real data & length
    WV_U32 takeup_length, // logical total length
    WV_U8 use_data,       // data insertion flag
    WV_U32 left,          // window left
    WV_U32 right          // window right
)
{
  if (seq->set_offset) {
    seq->offset = offset;
    seq->set_offset = 0;
  }

  if (left != 0 || right != 0) {
    if (left < seq->offset) {
      left = seq->offset;
    }
    WV_U32 right_limit = seq->offset + WV_CONFIG_SeqBufferSize >= seq->offset ? seq->offset + WV_CONFIG_SeqBufferSize : WV_U32_MAX;
    if (right > right_limit) {
      right = right_limit;
    }
    if (offset < left) {
      takeup_length -= left - offset;
      data = WV_SliceAfter(data, left - offset);
      offset = left;
    }
    if (offset + takeup_length > right) {
      takeup_length = right - offset;
      if (offset + data.length > right) {
        data = WV_SliceBefore(data, right - offset);
      }
    }
  }

  WV_U8 pos;
  for (pos = 0; pos < seq->used_count && seq->nodes[pos].left < offset; pos += 1)
    ;
  if (data.length == takeup_length && takeup_length != 0) {
    if (pos == 0 && seq->used_count == 0) {
      seq->nodes[0] = (WV_SeqMeta){ .left = offset, .right = offset + takeup_length };
      seq->used_count = 1;
    } else if (pos != 0) {
      if (offset <= seq->nodes[pos - 1].right) {
        assert(offset >= seq->nodes[pos - 1].left);
        assert(offset + takeup_length < seq->nodes[pos].left);
        seq->nodes[pos - 1].right = offset + takeup_length;
        if (pos < seq->used_count && seq->nodes[pos - 1].right >= seq->nodes[pos].left) {
          assert(seq->nodes[pos - 1].right <= seq->nodes[pos].right);
          seq->nodes[pos - 1].right = seq->nodes[pos].right;
          for (WV_U8 i = pos + 1; i < seq->used_count; i += 1) {
            seq->nodes[i - 1] = seq->nodes[i];
          }
          seq->used_count -= 1;
        }
      } else {
        if (pos < seq->used_count && offset + takeup_length >= seq->nodes[pos].left) {
          assert(offset + takeup_length <= seq->nodes[pos].right);
          seq->nodes[pos].left = offset;
        } else {
          for (WV_U8 i = seq->used_count; i > pos; i -= 1) {
            seq->nodes[i] = seq->nodes[i - 1];
          }
          seq->nodes[pos] = (WV_SeqMeta){ .left = offset, .right = offset + takeup_length };
          seq->used_count += 1;
        }
      }
    } else {
      if (seq->nodes[0].left <= offset + takeup_length) {
        assert(seq->nodes[0].right >= offset + takeup_length);
        seq->nodes[0].left = offset;
      } else {
        for (WV_U8 i = seq->used_count; i > 0; i -= 1) {
          seq->nodes[i] = seq->nodes[i - 1];
        }
        seq->nodes[0] = (WV_SeqMeta){ .left = offset, .right = offset + takeup_length };
        seq->used_count += 1;
      }
    }
  } else if (data.length != 0) {
    if (seq->used_count == 0) {
      seq->nodes[0] = (WV_SeqMeta){ .left = offset, .right = offset + data.length };
      seq->used_count = 1;
      seq->postfix = (WV_SeqMeta){ .left = offset + data.length, .right = offset + takeup_length };
    } else {
      assert(seq->nodes[seq->used_count - 1].left <= offset);
      if (seq->nodes[seq->used_count - 1].right <= offset) {
        seq->nodes[seq->used_count - 1].right = offset + data.length;
      } else {
        seq->nodes[seq->used_count] = (WV_SeqMeta){ .left = offset, .right = offset + data.length};
      }
      seq->postfix = (WV_SeqMeta){ .left = offset + data.length, .right = offset + takeup_length };
    }
  } else {
    if (!seq->has_post) {
      if (!seq->has_pre) {
        seq->prefix.left = offset;
        seq->has_pre = 1;
        seq->offset = seq->prefix.right = offset + takeup_length;
      } else if (offset <= seq->prefix.right) {
        assert(offset + takeup_length >= seq->prefix.right);
        seq->offset = seq->prefix.right = offset + takeup_length;
      } else {
        seq->postfix.left = offset;
        seq->postfix.right = offset + takeup_length;
        seq->has_post = 1;
      }
    } else {
      assert(offset + takeup_length >= seq->postfix.right);
      seq->postfix.right = offset + takeup_length;
    }
  }
  if (use_data && data.length != 0) {
    memcpy(&seq->buffer[offset - seq->offset], data.cursor, data.length);
  }
  return 0;
}

static inline WV_U8 WV_SeqReady(WV_Seq *seq)
{
  if (seq->used_count == 0)
  {
    return 1;
  }
  return seq->nodes[0].left == seq->offset && seq->used_count == 1;
}

static inline WV_ByteSlice WV_SeqAssemble(WV_Seq *seq, WV_Byte **need_free) {
  if (seq->used_count == 0 || seq->nodes[0].left != seq->offset) {
    *need_free = NULL;
    return WV_EMPTY;
  }
  WV_U32 ready_length = seq->nodes[0].right - seq->nodes[0].left;
  if (seq->used_count == 1) {
    *need_free = NULL;
    seq->offset = seq->nodes[0].right;
    seq->used_count = 0;
    return (WV_ByteSlice){ .cursor = seq->buffer, .length = ready_length };
  }

  WV_Byte *ready_buffer = malloc(sizeof(WV_Byte) * ready_length);
  memcpy(ready_buffer, &seq->buffer[seq->nodes[0].left - seq->offset], ready_length);
  seq->offset = seq->nodes[0].right;
  for (WV_U8 i = 1; i < seq->used_count; i += 1) {
    seq->nodes[i - 1] = seq->nodes[i];
  }
  seq->used_count -= 1;
  *need_free = ready_buffer;
  return (WV_ByteSlice){ .cursor = ready_buffer, .length = ready_length };
}

#endif