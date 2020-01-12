#ifndef WEAVER_RUNTIME_SEQ_H
#define WEAVER_RUNTIME_SEQ_H

#include "types.h"
#include <stdlib.h>
#include <string.h>

#define WV_CONFIG_SeqNodeCount 3
#define WV_CONFIG_SeqBufferSize (8 * (1 << 10))

typedef struct
{
    WV_U32 offset;
    WV_U32 length;
} WV_SeqMeta;

typedef struct
{
    WV_Byte *buffer;
    WV_U32 offset; // global offset of &buffer[0]
    WV_SeqMeta nodes[WV_CONFIG_SeqNodeCount];
    WV_U8 used_count;
    WV_U8 set_offset;
} WV_Seq;

static inline WV_U8 WV_InitSeq(WV_Seq *seq, WV_U8 use_data, WV_U32 zero_base)
{
    if (use_data)
    {
        seq->buffer = malloc(sizeof(WV_Byte) * WV_CONFIG_SeqBufferSize);
    }
    seq->offset = 0;
    seq->set_offset = !zero_base;
    seq->used_count = 0;
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

static inline WV_U8 WV_Insert(WV_Seq *seq, WV_U32 offset, WV_ByteSlice data, WV_U32 takeup_length, WV_U8 use_data)
{
    if (seq->set_offset)
    {
        seq->offset = offset;
        seq->set_offset = 0;
    }
    if (takeup_length == 0)
    {
        takeup_length = data.length;
    }
    if (seq->used_count == 0)
    {
        seq->used_count = 1;
        seq->nodes[0] = (WV_SeqMeta){.offset = offset, .length = takeup_length};
    }
    else
    {
        WV_U8 pos;
        for (pos = 0; pos < seq->used_count && offset > seq->nodes[pos].offset; pos += 1)
            ;
        // TODO: overlap
        WV_U8 mergable = pos < seq->used_count && (seq->nodes[pos].offset + seq->nodes[pos].length) == offset;
        if (pos != 0 && (seq->nodes[pos - 1].offset + seq->nodes[pos - 1].length) == offset)
        {
            seq->nodes[pos - 1].length += takeup_length;
            if (mergable)
            {
                seq->nodes[pos - 1].length += seq->nodes[pos].length;
                for (WV_U8 i = pos; i < seq->used_count; i += 1)
                {
                    seq->nodes[i] = seq->nodes[i + 1];
                }
                seq->used_count -= 1;
            }
        }
        else if (mergable)
        {
            seq->nodes[pos].offset -= takeup_length;
            seq->nodes[pos].length += takeup_length;
        }
        else
        {
            for (WV_U8 i = seq->used_count; i > pos; i -= 1)
            {
                seq->nodes[i] = seq->nodes[i - 1];
            }
            seq->nodes[pos] = (WV_SeqMeta){.offset = offset, .length = takeup_length};
            seq->used_count += 1;
        }
    }
    if (use_data)
    {
        memcpy(&seq->buffer[offset - seq->offset], data.cursor, data.length);
    }
    printf("used_count: %u\n", seq->used_count);
    for (int i = 0; i < seq->used_count; i += 1) {
        printf("offset: %u length: %u | ", seq->nodes[i].offset - seq->offset, seq->nodes[i].length);
    }
    printf("\n");
    return 0;
}

static inline WV_U8 WV_Crop(WV_Seq *seq, WV_U32 left, WV_U32 right, WV_U8 use_data)
{
    if (left > seq->offset)
    {
        WV_U8 first;
        for (first = 0; first < seq->used_count; first += 1)
        {
            if (seq->nodes[first].offset <= left)
            {
                if (seq->nodes[first].offset + seq->nodes[first].length <= left)
                {
                    //
                }
                else
                {
                    seq->nodes[first].offset = left;
                    seq->nodes[first].length -= left - seq->nodes[first].offset;
                    break;
                }
            }
        }
        for (WV_U8 i = first; i < seq->used_count; i += 1)
        {
            if (use_data)
            {
                WV_U32 target = seq->nodes[i].offset - left;
                memmove(&seq->buffer[target], &seq->buffer[seq->nodes[i].offset - seq->offset], seq->nodes[i].length);
            }
            seq->nodes[i - first] = seq->nodes[i];
        }
        seq->used_count -= first;
        seq->offset = left;
    }
    for (WV_U8 i = 0; i < seq->used_count; i += 1)
    {
        if (seq->nodes[i].offset + seq->nodes[i].length > right)
        {
            if (seq->nodes[i].offset < right)
            {
                seq->nodes[i].length = right - seq->nodes[i].offset;
                seq->used_count = i + 1;
            }
            else
            {
                seq->used_count = i;
            }
            break;
        }
    }
    return 0;
}

static inline WV_U8 WV_SeqReady(WV_Seq *seq)
{
    if (seq->used_count == 0)
    {
        return 1;
    }
    return seq->nodes[0].offset == seq->offset && seq->used_count == 1;
}

static inline WV_ByteSlice WV_SeqAssemble(WV_Seq *seq, WV_Byte **need_free)
{
    if (seq->used_count == 0 || seq->nodes[0].offset != seq->offset)
    {
        *need_free = NULL;
        return (WV_ByteSlice){.cursor = NULL, .length = 0};
    }

    WV_U32 ready_length = seq->nodes[0].length;
    seq->offset += ready_length;
    if (seq->used_count == 1)
    {
        seq->used_count = 0;
        *need_free = NULL;
        return (WV_ByteSlice){.cursor = seq->buffer, .length = ready_length};
    }

    WV_Byte *ready_buffer = malloc(sizeof(WV_Byte) * ready_length);
    memcpy(ready_buffer, seq->buffer, ready_length);

    for (int i = 1; i < seq->used_count; i += 1)
    {
        WV_U32 offset_now = seq->nodes[i].offset - seq->offset;
        WV_U32 offset_prev = offset_now + ready_length;
        memmove(&seq->buffer[offset_now], &seq->buffer[offset_prev], seq->nodes[i].length);
        seq->buffer[i - 1] = seq->buffer[i];
    }
    seq->used_count -= 1;

    *need_free = ready_buffer;
    return (WV_ByteSlice){.cursor = ready_buffer, .length = ready_length};
}

#endif