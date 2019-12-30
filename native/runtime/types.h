#ifndef WEAVER_RUNTIME_TYPES_H
#define WEAVER_RUNTIME_TYPES_H

#include <stdint.h>
#include <netinet/in.h>

typedef uint8_t WV_Byte;
typedef uint8_t WV_U8;
typedef uint16_t WV_U16;
typedef uint32_t WV_U32;
typedef uint64_t WV_U64;
typedef double WV_F;
typedef void *WV_Any;

static inline WV_U16 WV_HToN16(WV_U16 x) {
    return htons(x);
}

static inline WV_U32 WV_HToN32(WV_U32 x) {
    return htonl(x);
}

#endif