#include "table.h"
#include <assert.h>

typedef struct Key {
    WV_U32 a;
    WV_U32 b;
} Key;

typedef struct Value {
    WV_INST_EXTRA_DECL
    WV_U64 x;
} Value;

int main(void) {
    WV_Table table;
    WV_InitTable(&table, 0);

    {
        WV_ByteSlice k1 = { .cursor = (WV_Byte *)&(Key){ .a = 0, .b = 0 }, .length = sizeof(Key) };
        assert(WV_FetchInst(&table, k1) == NULL);
        Value *v1 = WV_CreateInst(&table, k1, sizeof(Value));
        v1->x = 0;
        Value *v2 = WV_FetchInst(&table, k1);
        assert(v2 == v1);
        WV_DestroyInst(&table, k1);
        assert(WV_FetchInst(&table, k1) == NULL);
    }

    {
        for (WV_U32 a = 1234; a < 5678; a += 1) {
            for (WV_U32 b = 543; b > 345; b -= 1) {
                WV_ByteSlice k1 = { .cursor = (WV_Byte *)&(Key){ .a = a, .b = b }, .length = sizeof(Key) };
                assert(WV_FetchInst(&table, k1) == NULL);
                Value *v1 = WV_CreateInst(&table, k1, sizeof(Value));
                v1->x = a + b;
            }
        }
        for (WV_U32 b = 345 + 1; b <= 543; b += 1) {
            for (WV_U32 a = 5678 - 1; a >= 1234; a -= 1) {
                WV_ByteSlice k1 = { .cursor = (WV_Byte *)&(Key){ .a = a, .b = b }, .length = sizeof(Key) };
                assert(((Value *)WV_FetchInst(&table, k1))->x == a + b);
                WV_DestroyInst(&table, k1);
            }
        }
    }

    WV_CleanTable(&table);
    return 0;
}