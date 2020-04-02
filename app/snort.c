#include <stdio.h>
#include <weaver.h>

WV_U8 WV_Setup()
{
    printf("global setup...\n");
    return 0;
}

typedef struct {
  WV_U8 _203;  // report_status.state
  WV_ByteSlice _204;  // report_status.content
}__attribute__((packed)) H12;

WV_U8 report_status(H12 *args, WV_Any user_data)
{
    printf("state: %u len(content): %u\n", args->_203, args->_204.length);
    return 0;
}
