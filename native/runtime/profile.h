#ifndef WEAVER_RUNTIME_PROFILE_H
#define WEAVER_RUNTIME_PROFILE_H

#include "types.h"

typedef struct _WV_Profile {
    WV_U64 interval_byte_count;
    WV_U32 interval_packet_count;
    WV_U32 next_checkpoint_sec;
    WV_F last_record_sec;
    WV_F last_10_throughput[10];
    WV_F record_count;
} WV_Profile;

WV_U8 WV_ProfileStart(WV_Profile *);

WV_U8 WV_ProfileRecord(WV_Profile *, WV_U32, WV_U8);

#endif