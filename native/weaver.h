// Weaver Runtime Header
#ifndef WV_WEAVER_H
#define WV_WEAVER_H

#include "runtime/malloc.h"
#include "runtime/profile.h"
#include "runtime/seq.h"
#include "runtime/types.h"
#include <stdlib.h>
#include <string.h>

// implemented by blackbox
typedef struct _WV_Runtime WV_Runtime;
WV_U8 WV_ProcessPacket(WV_ByteSlice, WV_Runtime *);
WV_Runtime *WV_AllocRuntime();
WV_U8 WV_FreeRuntime(WV_Runtime *);
WV_Profile *WV_GetProfile(WV_Runtime *);
// blackbox implemented end

// implemented by whitebox
WV_U8 WV_Setup();
// whitebox implemented end

#endif