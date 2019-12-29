#include "weaver.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

WV_U8 WV_InitRuntime(WV_Runtime *runtime) {
    printf("table count: %d\n", WV_CONFIG_TABLE_COUNT);
    runtime->tables = malloc(sizeof(WV_Table) * WV_CONFIG_TABLE_COUNT);
    if (!runtime->tables) {
        return 1;
    }
    for (WV_U8 i = 0; i < WV_CONFIG_TABLE_COUNT; i += 1) {
        tommy_hashdyn_init(&runtime->tables[i]);
    }
    return 0;
}

WV_U8 WV_CleanRuntime(WV_Runtime *runtime) {
    for (WV_U8 i = 0; i < WV_CONFIG_TABLE_COUNT; i += 1) {
        tommy_hashdyn_foreach(&runtime->tables[i], free);
        tommy_hashdyn_done(&runtime->tables[i]);
    }
    return 0;
}

WV_U8 WV_ProfileStart(WV_Runtime *runtime) {
    memset(&runtime->profile, 0, sizeof(WV_Profile));
    WV_F current = clock() / CLOCKS_PER_SEC;
    runtime->profile.last_record_sec = current;
    runtime->profile.next_checkpoint_sec = (WV_U32)current + 1;
}

WV_U8 WV_ProfileRecord(WV_Runtime *runtime, WV_U32 byte_length, WV_U8 status) {
    // TODO: use status
    WV_Profile *profile = &runtime->profile;
    profile->interval_byte_count += byte_length;
    WV_F current = (WV_F)clock() / CLOCKS_PER_SEC;
    if (current < profile->next_checkpoint_sec) {
        return 0;
    }
    WV_F interval = current - profile->last_record_sec;
    WV_F throughput = profile->interval_byte_count / interval / (1 << 30) * 8;
    printf("checkpoint: %f ms, throughput: %f Gbps\n", current * 1000, throughput);

    profile->interval_byte_count = 0;
    profile->next_checkpoint_sec += 1;
    profile->last_record_sec = current;
    return 0;
}
