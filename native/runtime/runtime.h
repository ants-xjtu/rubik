#ifndef WEAVER_RUNTIME_RUNTIME_H
#define WEAVER_RUNTIME_RUNTIME_H

#include "table.h"
#include "profile.h"

typedef struct _WV_Runtime {
    WV_Table *tables;
    WV_Profile profile;
} WV_Runtime;

WV_U8 WV_InitRuntime(WV_Runtime *);

WV_U8 WV_CleanRuntime(WV_Runtime *);

#endif