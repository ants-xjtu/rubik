#include "runtime.h"
#include "table.h"
#include <stdlib.h>

WV_U8 WV_InitRuntime(WV_Runtime *runtime) {
    runtime->tables = malloc(sizeof(WV_Table) * WV_CONFIG_TABLE_COUNT);
    if (!runtime->tables) {
        return 1;
    }
    for (WV_U8 i = 0; i < WV_CONFIG_TABLE_COUNT; i += 1) {
        WV_InitTable(&runtime->tables[i], i);
    }
    return 0;
}

WV_U8 WV_CleanRuntime(WV_Runtime *runtime) {
    for (WV_U8 i = 0; i < WV_CONFIG_TABLE_COUNT; i += 1) {
        WV_CleanTable(&runtime->tables[i]);
    }
    free(runtime->tables);
    return 0;
}
