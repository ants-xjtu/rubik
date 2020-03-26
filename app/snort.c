#include <stdio.h>
#include <weaver.h>

WV_U8 WV_Setup()
{
    printf("global setup...\n");
    return 0;
}

typedef struct {
    WV_U8 _190; // report_status.state
    WV_ByteSlice _191; // report_status.content
} H10;

WV_U8 report_status(H10* args, WV_Any user_data)
{
    printf("state: %u len(content): %u\n", args->_190, args->_191.length);
    return 0;
}

typedef struct {
  WV_U8 _200;  // count_ip.dummy
} H11;

WV_U8 count_ip(H11 *args, WV_Any user_data) {
  printf("count ip\n");
  return 0;
}