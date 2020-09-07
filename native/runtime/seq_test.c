#include <assert.h>
#include <string.h>
#include "seq.h"

void test_create()
{
    WV_Seq seq;
    WV_InitSeq(&seq, 1, 0);
    WV_CleanSeq(&seq, 1);
}

void test_insert()
{
    WV_Seq seq;
    WV_InitSeq(&seq, 1, 0);
    WV_Byte buf[100];
    memset(buf, 0xCC, sizeof(buf));
    WV_ByteSlice payload = {.cursor = buf, .length = sizeof(buf)};
    WV_Insert(&seq, 0, payload, sizeof(buf), 1, 0, 1024);
    WV_Byte *free_ptr;
    WV_ByteSlice assembled = WV_SeqAssemble(&seq, &free_ptr, 1);
    assert(assembled.length == payload.length);
    assert(memcmp(assembled.cursor, payload.cursor, sizeof(assembled.length)) == 0);
}

void (*TESTCASES[])() = {
    test_create, test_insert, NULL};

int main()
{
    for (int i = 0; TESTCASES[i] != NULL; i += 1)
    {
        TESTCASES[i]();
    }
    return 0;
}