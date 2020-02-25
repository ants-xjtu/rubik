#ifndef WEAVER_RUNTIME_SEQ_H
#define WEAVER_RUNTIME_SEQ_H

#include "types.h"
#include "malloc.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

#define WV_CONFIG_SeqNodeCount 32
#define WV_CONFIG_SeqBufferSize (8 * (1 << 10))

typedef struct {
    WV_U32 left;
    WV_U32 right;
} WV_SeqMeta;

typedef struct {
    WV_Byte* buffer;
    WV_U32 offset;
    WV_U8 set_offset;
    WV_SeqMeta nodes[WV_CONFIG_SeqNodeCount], postfix;
    WV_U8 used_count;
    WV_U8 pre_done, post_start;
} WV_Seq;

static inline WV_U8 WV_InitSeq(WV_Seq* seq, WV_U8 use_data, WV_U32 zero_base)
{
    if (use_data) {
        seq->buffer = WV_Malloc(sizeof(WV_Byte) * WV_CONFIG_SeqBufferSize);
    } else {
        seq->buffer = NULL;
    }
    seq->offset = 0;
    seq->set_offset = !zero_base;
    seq->used_count = 0;
    seq->postfix = (WV_SeqMeta){ .left = 0, .right = 0 };
    seq->pre_done = seq->post_start = 0;
    return 0;
}

static inline WV_U8 WV_CleanSeq(WV_Seq* seq, WV_U8 use_data)
{
    if (use_data) {
        WV_Free(seq->buffer);
    }
    return 0;
}

static inline WV_U8 WV_SeqEmptyAlign(WV_Seq* seq, WV_U32 offset, WV_ByteSlice data, WV_U32 takeup_length)
{
    // printf("EmptyAlign\n");
    return seq->used_count == 0 && seq->offset == offset && data.length == takeup_length;
}

static inline WV_U8 _AssertNodes(WV_Seq* seq)
{
    // printf("%u\n", seq->post_start);
    for (WV_U8 i = 0; i < seq->used_count; i += 1) {
        assert(seq->nodes[i].left < seq->nodes[i].right);
        assert(seq->nodes[i].left >= seq->offset);
        assert(seq->nodes[i].right - seq->offset <= WV_CONFIG_SeqBufferSize);
    }
    for (WV_U8 i = 1; i < seq->used_count; i += 1) {
        assert(seq->nodes[i - 1].right < seq->nodes[i].left);
    }
    // printf("%u\n", seq->post_start);
    if (seq->post_start) {
        assert(seq->postfix.left < seq->postfix.right);
        // assert(seq->postfix.left >= seq->offset);
    }
    if (seq->post_start && seq->used_count != 0) {
        assert(seq->nodes[seq->used_count - 1].right <= seq->postfix.left);
    }
    return 0;
}

static inline WV_U8 _InsertNode(WV_Seq* seq, WV_U8 index)
{
    assert(seq->used_count < WV_CONFIG_SeqNodeCount - 1);
    for (WV_U8 i = seq->used_count; i > index; i -= 1) {
        seq->nodes[i] = seq->nodes[i - 1];
    }
    seq->used_count += 1;
    return 0;
}

static inline WV_U8 _RemoveNode(WV_Seq* seq, WV_U8 index)
{
    assert(seq->used_count > index);
    for (WV_U8 i = index; i < seq->used_count; i += 1) {
        seq->nodes[i] = seq->nodes[i + 1];
    }
    seq->used_count -= 1;
    return 0;
}

static inline WV_U8 WV_Insert(
    WV_Seq* seq,
    WV_U32 offset, // offset position of data
    WV_ByteSlice data, // real data & length
    WV_U32 takeup_length, // logical total length
    WV_U8 use_data, // data insertion flag
    WV_U32 left, // window left
    WV_U32 right // window right
)
{
    // printf("%u %u\n", takeup_length, data.length);
    if (seq->set_offset) {
        seq->offset = offset;
        seq->set_offset = 0;
    }

    if (takeup_length == 0) {
        takeup_length = data.length;
    }
    assert(data.length <= takeup_length);
    // printf("%u %u %u %u %u %u %u\n", offset, data.length, takeup_length, left, right, seq->post_start, seq->postfix.left);
    // printf("used_count: %u\n", seq->used_count);
    // printf("seq->offset: %u\n", seq->offset);
    // printf("%u %u %u %u %u\n", offset, data.length, takeup_length, left, right);
    if (left != 0 || right != 0) {
        assert(left <= right);

        while (seq->used_count > 0) {
            if (seq->nodes[0].right <= left) {
                _RemoveNode(seq, 0);
            } else {
                if (seq->nodes[0].left < left) {
                    seq->nodes[0].left = left;
                }
                break;
            }
        }
        for (WV_U8 i = 0; i < seq->used_count; i += 1) {
            if (seq->nodes[i].right > right) {
                if (seq->nodes[i].left >= right) {
                    seq->used_count = i;
                } else {
                    seq->nodes[i].right = right;
                    seq->used_count = i + 1;
                }
                break;
            }
        }
        if (seq->offset < left) {
            // left expected data out of window
            for (WV_U8 i = 0; i < seq->used_count; i += 1) {
                assert(seq->nodes[i].left >= left);
                assert(seq->nodes[i].right - seq->offset <= WV_CONFIG_SeqBufferSize);
                memmove(
                    &seq->buffer[seq->nodes[i].left - left],
                    &seq->buffer[seq->nodes[i].left - seq->offset],
                    seq->nodes[i].right - seq->nodes[i].left);
            }
            // printf("%u %u\n", seq->offset, left);
            seq->offset = left;
        }

        if (offset >= right || offset + takeup_length < left) {
            // full out of window
            takeup_length = data.length = 0;
        } else {
            if (offset < left) {
                // left out of window
                takeup_length -= left - offset;
                data = WV_SliceAfter(data, left - offset);
                offset = left;
            }
            if (offset + takeup_length > right) {
                // right out of window
                takeup_length = right - offset;
                if (offset + data.length > right) {
                    data = WV_SliceBefore(data, right - offset);
                }
            }
        }
    }
    // printf("used_count: %u\n", seq->used_count);
    assert(takeup_length < 3000);
    _AssertNodes(seq);

    WV_U8 pos;
    for (pos = 0; pos < seq->used_count && seq->nodes[pos].left < offset; pos += 1)
        ;
    // printf("%u %u %u\n", seq->used_count, seq->post_start, seq->postfix.left);
    if (takeup_length != 0) {
        if (offset < seq->offset) {
            // hard out of order
            data = WV_EMPTY;
        } else if (seq->post_start && offset + data.length > seq->postfix.left) {
            // hard out of window
            data = WV_EMPTY;
        } else if (data.length != 0) {
            // assert(offset >= seq->offset);
            if (pos != 0 && offset <= seq->nodes[pos - 1].right) {
                // possible overlap/retrx
                assert(offset >= seq->nodes[pos - 1].left);
                if (offset + data.length > seq->nodes[pos - 1].right) {
                    seq->nodes[pos - 1].right = offset + data.length;
                }
                pos = pos - 1;
            } else {
                _InsertNode(seq, pos);
                seq->nodes[pos] = (WV_SeqMeta){ .left = offset, .right = offset + data.length };
            }
            // printf("before while#1\n");
            while (pos + 1 < seq->used_count && seq->nodes[pos].right >= seq->nodes[pos + 1].left) {
                // possible overlap/retrx
                if (seq->nodes[pos].right < seq->nodes[pos + 1].right) {
                    seq->nodes[pos].right = seq->nodes[pos + 1].right;
                }
                _RemoveNode(seq, pos + 1);
            }
            // printf("after while#1\n");
            seq->pre_done = 1;

            if (data.length != takeup_length && !seq->post_start) {
                assert(!seq->post_start);
                // printf("set post_start #1\n");
                seq->post_start = 1;
                seq->postfix = (WV_SeqMeta){ .left = offset + data.length, .right = offset + takeup_length };
            }
        } else {
            if (seq->post_start) {
                // assert(offset == seq->postfix.right);
                if (offset == seq->postfix.right) {
                    seq->postfix.right = offset + takeup_length;
                } else {
                    // postfix out of window
                }
            } else if (!seq->pre_done) {
                // assert(offset == seq->offset);
                if (offset = seq->offset) {
                    seq->offset = offset + takeup_length;
                } else {
                    // prefix out of window
                }
            } else {
                if (seq->used_count == 0 || offset >= seq->nodes[seq->used_count - 1].right) {
                    // printf("set post_start #2\n");
                    seq->post_start = 1;
                    seq->postfix = (WV_SeqMeta){ .left = offset, .right = offset + takeup_length };
                } else {
                    // postfix out of window, ignore
                }
            }
        }
    }
    if (seq->used_count > 0 && seq->nodes[seq->used_count - 1].right - seq->offset > WV_CONFIG_SeqBufferSize) {
        if (seq->nodes[seq->used_count - 1].left - seq->offset < WV_CONFIG_SeqBufferSize) {
            // right out of memory
            seq->nodes[seq->used_count - 1].right = seq->offset + WV_CONFIG_SeqBufferSize;
            data = WV_SliceBefore(data, seq->offset + WV_CONFIG_SeqBufferSize - offset);
        } else {
            // full out of memory
            seq->used_count -= 1;
            data = WV_EMPTY;
        }
    }
    _AssertNodes(seq);

    if (use_data && data.length != 0) {
        assert(offset >= seq->offset);
        assert(offset - seq->offset + data.length <= WV_CONFIG_SeqBufferSize);
        // printf("memcpy (insert)\n");
        WV_Memcpy(&seq->buffer[offset - seq->offset], data.cursor, data.length);
    }
    return _AssertNodes(seq);
}

static inline WV_U8 WV_SeqReady(WV_Seq* seq)
{
    // printf("used_count: %u\n", seq->used_count);
    if (seq->used_count > 0 && seq->nodes[0].left != seq->offset) {
        return 0;
    }
    // printf("offset: %u\n", seq->offset);
    if (!seq->post_start) {
        return 1;
    }
    if (seq->used_count == 0) {
        // printf("offset: %u postfix.left: %u\n", seq->offset, seq->postfix.left);
        return seq->offset >= seq->postfix.left;
    } else {
        // printf("nodes[0].right: %u postfix.left: %u\n", seq->nodes[0].right, seq->postfix.left);
        return seq->nodes[0].right == seq->postfix.left;
    }
}

static inline WV_ByteSlice WV_SeqAssemble(WV_Seq* seq, WV_Byte** need_free)
{
    // printf("%u %u\n", seq->used_count, seq->offset);
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

    WV_Byte* ready_buffer = WV_Malloc(sizeof(WV_Byte) * ready_length);
    // printf("memcpy\n");
    WV_Memcpy(ready_buffer, &seq->buffer[seq->nodes[0].left - seq->offset],
        ready_length);
    seq->offset = seq->nodes[0].right;
    _RemoveNode(seq, 0);
    *need_free = ready_buffer;
    return (WV_ByteSlice){ .cursor = ready_buffer, .length = ready_length };
}

#endif