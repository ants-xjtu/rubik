#ifndef WEAVER_RUNTIME_MALLOC_H
#define WEAVER_RUNTIME_MALLOC_H

#ifdef WV_TARGET_dpdk
#include <rte_malloc.h>
#include <rte_memcpy.h>
#define WV_Malloc(n) rte_malloc(NULL, n, 0)
#define WV_Free rte_free
#define WV_Memcpy rte_memcpy
#else
#include <stdlib.h>
#include <string.h>
#define WV_Malloc malloc
#define WV_Free free
#define WV_Memcpy memcpy
#endif

#endif