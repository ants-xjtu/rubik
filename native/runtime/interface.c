#include "weaver.h"
#include <stdio.h>
#include <stdlib.h>

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
