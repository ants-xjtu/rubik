#include "seq.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

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
  WV_CleanSeq(&seq, 1);
}

void test_insert_out_of_order() {
  WV_Seq seq;
  WV_InitSeq(&seq, 1, 1);
  WV_Byte buf[100];
  memset(buf, 0xCC, sizeof(buf));
  WV_ByteSlice payload = {.cursor = buf, .length = sizeof(buf)};
  WV_Insert(&seq, sizeof(buf), payload, sizeof(buf), 1, 0, 65536);
  WV_Byte *free_ptr;
  assert(WV_SeqAssemble(&seq, &free_ptr, 1).length == 0);
  memset(buf, 0xCD, sizeof(buf));
  WV_Insert(&seq, 0, payload, sizeof(buf), 1, 0, 65536);
  WV_ByteSlice assembled = WV_SeqAssemble(&seq, &free_ptr, 1);
  assert(assembled.length == 2 * sizeof(buf));
  for (int i = 0; i < 2 * sizeof(buf); i += 1) {
    assert(assembled.cursor[i] == (i < sizeof(buf) ? 0xCD : 0xCC));
  }
  if (free_ptr != NULL) {
    free(free_ptr);
  }
  WV_CleanSeq(&seq, 1);
}

void (*TESTCASES[])() = {
  test_create, test_insert_in_order, test_insert_out_of_order, NULL};

int main() {
  for (int i = 0; TESTCASES[i] != NULL; i += 1) {
    TESTCASES[i]();
  }
  return 0;
}