#include "table.h"
#include <assert.h>

int main(void) {
    struct {
        struct {
            WV_U32 a;
            WV_U32 b;
        } k1;
        struct {
            WV_U32 c;
            WV_U32 d;
        } k2;
    } k_alloc, *k = &k_alloc;
    struct {
        WV_U32 a;
        WV_U32 b;
    } *k1 = (WV_Any)&k->k1;
    struct {
        WV_U32 c;
        WV_U32 d;
    } *k2 = (WV_Any)&k->k2;

    struct {
        WV_BI_INST_EXTRA_DECL(sizeof(*k))
        WV_U64 x;
    } *v;

    WV_Table table;
    WV_InitTable(&table, 0);
    {
        assert(sizeof(*k1) + sizeof(*k2) == sizeof(*k));
        assert(&k1->a == &k->k1.a);
        k1->a = 0;
        k1->b = 1;
        k2->c = 2;
        k2->d = 3;
        WV_ByteSlice key = { .cursor = (WV_Byte *)k, .length = sizeof(*k) };
        assert(WV_FetchInst(&table, key) == NULL);
        WV_ByteSlice half_key1 = { .cursor = (WV_Byte *)k1, .length = sizeof(*k1) };
        WV_ByteSlice half_key2 = { .cursor = (WV_Byte *)k2, .length = sizeof(*k2) };
        v = WV_CreateBiInst(&table, half_key1, half_key2, sizeof(*v));
        v->x = 1;
        WV_BiInstHeader(sizeof(*k)) *h = WV_FetchInst(&table, key);
        assert(h != NULL);
        assert(h->reverse == 0);
        v = WV_InstData(h, sizeof(*k));
        assert(v->x == 1);
        v->x = 2;

        k1->a = 2;
        k1->b = 3;
        k2->c = 0;
        k2->d = 1;
        h = WV_FetchInst(&table, key);
        assert(h != NULL);
        assert(h->reverse == 1);
        v = WV_InstData(h, sizeof(*k));
        assert(v->x == 2);

        WV_DestroyBiInst(&table, key);
        assert(WV_FetchInst(&table, key) == NULL);
        k1->a = 0;
        k1->b = 1;
        k2->c = 2;
        k2->d = 3;
        v = WV_CreateBiInst(&table, half_key1, half_key2, sizeof(*v));
        WV_DestroyBiInst(&table, key);
        assert(WV_FetchInst(&table, key) == NULL);
    }

    WV_CleanBiTable(&table, sizeof(*k));

    return 0;
}