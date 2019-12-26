// Weaver Runtime Header
#ifndef WV_WEAVER_H
#define WV_WEAVER_H

#include <stdint.h>

typedef uint8_t WV_Byte;
typedef uint8_t WV_U8;
typedef uint32_t WV_U32;

typedef struct WV_Runtime {
    //
} WV_Runtime;

WV_U8 WV_ProcessPacket(WV_Byte *, WV_U32, WV_Runtime *);

#endif