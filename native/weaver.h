// Weaver Runtime Header
#ifndef WV_WEAVER_H
#define WV_WEAVER_H

#include <stdlib.h>
#include <string.h>
#include "runtime/types.h"
#include "runtime/seq.h"
#include "runtime/profile.h"

// implemented by blackbox
typedef struct _WV_Runtime WV_Runtime;
WV_U8 WV_ProcessPacket(WV_ByteSlice, WV_Runtime *);
WV_Runtime *WV_AllocRuntime();
WV_U8 WV_FreeRuntime(WV_Runtime *);
WV_Profile *WV_GetProfile(WV_Runtime *);
// blackbox implemented end

#endif