#include "seq.h"
#include <assert.h>
#include <string.h>
#include <stdlib.h>

void test_create() {
  WV_Seq seq;
  WV_InitSeq(&seq, 1, 0);
  WV_CleanSeq(&seq, 1);
}

void test_insert_in_order() {
  WV_Seq seq;
  WV_InitSeq(&seq, 1, 0);
  WV_Byte buf[100];
  for (int i = 0; i < 100; i += 1) {
    memset(buf, i, sizeof(buf));
    WV_ByteSlice payload = {.cursor = buf, .length = sizeof(buf)};
    WV_Insert(&seq, i * sizeof(buf), payload, sizeof(buf), 1, 0, 65536);
    WV_Byte *free_ptr;
    WV_ByteSlice assembled = WV_SeqAssemble(&seq, &free_ptr, 1);
    assert(assembled.length == payload.length);
    assert(
      memcmp(assembled.cursor, payload.cursor, sizeof(assembled.length)) == 0);
    if (free_ptr != NULL) {
        free(free_ptr);
    }
  }
}

void test_insert_out_of_order() {

}

void (*TESTCASES[])() = {test_create, test_insert_in_order, NULL};

int main() {
  for (int i = 0; TESTCASES[i] != NULL; i += 1) {
    TESTCASES[i]();
  }
  return 0;
}