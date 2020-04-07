#include <stdio.h>
#include <weaver.h>
#include <assert.h>
#include <stdlib.h>
#include "libac/acism.h"
#include "http-parser/http_parser.h"
#include <libconfig.h>


WV_U8 WV_Setup()
{
  printf("global setup...\n");
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
  //
}

WV_U8 report_status(H12 *args, WV_Any *user_data_)
{
  WV_U8 state = args->_203;
  WV_ByteSlice sdu = args->_204;

  if (state != 3) {
    return 0;
  }

  //

  return 0;
}
