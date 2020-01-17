#include "profile.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

WV_U8 WV_ProfileStart(WV_Profile* profile)
{
    memset(profile, 0, sizeof(WV_Profile));
    WV_F current = clock() / CLOCKS_PER_SEC;
    profile->last_record_sec = current;
    profile->next_checkpoint_sec = (WV_U32)current + 1;
}

WV_U8 WV_ProfileRecord(WV_Profile* profile, WV_U32 byte_length, WV_U8 status)
{
    // TODO: use status
    profile->interval_byte_count += byte_length;
    profile->interval_packet_count += 1;
    if (profile->interval_packet_count % 1000000 != 0) {
        return 0;
    }
    WV_F current = (WV_F)clock() / CLOCKS_PER_SEC;
    if (current < profile->next_checkpoint_sec) {
        return 0;
    }

    WV_ProfileRecordPrint(profile);

    profile->interval_byte_count = 0;
    profile->interval_packet_count = 0;
    profile->next_checkpoint_sec = (WV_U32)current + 2;
    profile->last_record_sec = current;
    return 0;
}

WV_U8 WV_ProfileRecordPrint(WV_Profile* profile)
{
    WV_F current = (WV_F)clock() / CLOCKS_PER_SEC;
    WV_F interval = current - profile->last_record_sec;
    WV_F throughput = profile->interval_byte_count / interval / 1e9 * 8;

    profile->last_10_throughput[profile->record_count % 10] = throughput;
    profile->record_count += 1;
    WV_U8 count = 10;
    if (count > profile->record_count) {
        count = profile->record_count;
    }
    WV_F throughput_avg = 0;
    for (WV_U8 i = 0; i < count && i < 10; i += 1) {
        throughput_avg += profile->last_10_throughput[i];
    }
    throughput_avg /= count;

    printf("checkpoint: %f ms, throughput: %f(%f) Gbps (last %d avg.)\n", current * 1000, throughput, throughput_avg, count);
    return 0;
}