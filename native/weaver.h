// Weaver Runtime Header
#ifndef WV_WEAVER_H
#define WV_WEAVER_H

#include <stdint.h>

typedef int32_t WV_I32;
typedef uint32_t WV_U32;
typedef uint8_t WV_Byte;

typedef struct WV_Runtime {
    //
} WV_Runtime;

WV_I32 WV_ProcessPacket(WV_Byte *, WV_U32, WV_Runtime *);

#endif