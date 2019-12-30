// Weaver Runtime Header
#ifndef WV_WEAVER_H
#define WV_WEAVER_H

#include "runtime/types.h"
#include "runtime/slice.h"
#include "runtime/table.h"
#include "runtime/seq.h"
#include "runtime/profile.h"
#include "runtime/runtime.h"

WV_U8 WV_ProcessPacket(WV_ByteSlice, WV_Runtime *);

#endif