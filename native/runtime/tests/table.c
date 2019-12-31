#include "table.h"
#include <assert.h>

typedef struct Key {
    WV_U32 a;
    WV_U32 b;
} Key;

typedef struct Value {
    WV_INST_EXTRA_DECL(sizeof(Key))
    WV_U64 x;
} Value;

int main(void) {
    WV_Table table;
    WV_InitTable(&table, 0);

    {
        WV_ByteSlice k1 = { .cursor = (WV_Byte *)&(Key){ .a = 0, .b = 0 }, .length = sizeof(Key) };
        assert(WV_FetchInstHeader(&table, k1) == NULL);
        WV_InstHeader(sizeof(k1)) *f1 = WV_CreateInst(&table, k1, sizeof(Value));
        assert(f1 != NULL);
        Value *v1 = (WV_Any)f1;
        v1->x = 0;
        WV_InstHeader(sizeof(k1)) *f2 = WV_FetchInstHeader(&table, k1);
        assert((WV_Any)f2 == (WV_Any)f1);
        WV_DestroyInst(&table, k1);
        assert(WV_FetchInstHeader(&table, k1) == NULL);
    }

    {
        for (WV_U32 a = 1234; a < 5678; a += 1) {
            for (WV_U32 b = 543; b > 345; b -= 1) {
                WV_ByteSlice k1 = { .cursor = (WV_Byte *)&(Key){ .a = a, .b = b }, .length = sizeof(Key) };
                assert(WV_FetchInstHeader(&table, k1) == NULL);
                Value *v1 = WV_CreateInst(&table, k1, sizeof(Value));
                v1->x = a + b;
            }
        }
        for (WV_U32 b = 345 + 1; b <= 543; b += 1) {
            for (WV_U32 a = 5678 - 1; a >= 1234; a -= 1) {
                WV_ByteSlice k1 = { .cursor = (WV_Byte *)&(Key){ .a = a, .b = b }, .length = sizeof(Key) };
                assert(((Value *)WV_FetchInstHeader(&table, k1))->x == a + b);
                WV_DestroyInst(&table, k1);
            }
        }
    }

    WV_CleanTable(&table);
    return 0;
}