#include <stdio.h>
#include <weaver.h>
#include <assert.h>
#include <stdlib.h>
#include "libac/acism.h"


WV_ByteSlice read_length_value(FILE *data) {
  WV_Byte lenbuf[2];
  if (fread(lenbuf, sizeof(WV_Byte), 2, data) != 2) {
    return WV_EMPTY;
  }
  WV_U16 length = (lenbuf[0] << 8) + lenbuf[1];
  WV_Byte *value = malloc(sizeof(WV_Byte) * length);
  assert(fread(value, sizeof(WV_Byte), length, data) == length);
  return (WV_ByteSlice){.cursor = value, .length = length};
}

MEMREF contents[10000];
WV_ByteSlice messages[10000];
WV_U16 content_count;
ACISM *global_ac;

WV_U8 WV_Setup()
{
  printf("global setup...\n");
  FILE *rules_data = fopen("snort.bin", "rb");
  content_count = 10000;
  for (WV_U16 i = 0; i < 10000; i += 1) {
    WV_ByteSlice message = read_length_value(rules_data);
    if (message.length == 0) {
      content_count = i;
      break;
    }
    messages[i] = message;    
    WV_ByteSlice content = read_length_value(rules_data);
    // printf("content: %*s\n", content.length, content.cursor);
    contents[i].len = content.length;
    contents[i].ptr = content.cursor;
  }

  global_ac = acism_create(contents, content_count);
  fclose(rules_data);
  return 0;
}

typedef struct {
  WV_U8 _203;  // report_status.state
  WV_ByteSlice _204;  // report_status.content
}__attribute__((packed)) H12;

typedef struct {
  WV_I32 state;
} UserData;

int on_match(int strnum, int textpos, void *context) {
  printf("match: %*s\n", messages[strnum].length, messages[strnum].cursor);
}

WV_U8 report_status(H12 *args, WV_Any *user_data_)
{
  WV_U8 state = args->_203;
  WV_ByteSlice sdu = args->_204;
  printf("state: %u len(sdu): %u\n", state, sdu.length);

  if (state != 3) {
    return 0;
  }

  UserData *user_data = NULL;
  if (state == 3 && *user_data_ == NULL) {
    *user_data_ = malloc(sizeof(UserData));
    user_data = *user_data_;
    user_data->state = 0;
  }
  user_data = *user_data_;

  MEMREF text = {.ptr = sdu.cursor, .len = sdu.length};
  acism_more(global_ac, text, on_match, NULL, &user_data->state);

  return 0;
}
