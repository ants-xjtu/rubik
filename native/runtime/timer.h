#ifndef WEAVER_NATIVE_RUNTIME_TIMER_H
#define WEAVER_NATIVE_RUNTIME_TIMER_H

#include "types.h"
#include <sys/time.h>

#define TIMEOUT 30

#define TIMER_FIELDS(inst_type) \
    inst_type *inst_type##_timer_head, *inst_type##_timer_last;

#define TIMER_INJECT_FIELDS(inst_type) \
    struct inst_type *prev, *next; \
    WV_U64 last_update;

#define TIMER_INIT(rt, inst_type) \
    rt->inst_type##_timer_head = rt->inst_type##_timer_last = NULL

#define TIMER_INSERT(rt, inst_type, inst) \
    if (rt->inst_type##_timer_last == NULL) { \
        rt->inst_type##_timer_head = rt->inst_type##_timer_last = inst; \
        inst->prev = inst->next = NULL; \
    } else { \
        inst->prev = NULL; \
        inst->next = rt->inst_type##_timer_head; \
        rt->inst_type##_timer_head->prev = inst; \
        rt->inst_type##_timer_head = inst; \
    } \
    struct timeval tv; \
    gettimeofday(&tv, NULL); \
    inst->last_update = tv.tv_sec

#define TIMER_FETCH(rt, inst_type, inst) \
    if (inst->prev != NULL) { \
        inst->prev->next = inst->next; \
    } \
    if (inst->next != NULL) { \
        inst->next->prev = inst->prev; \
    } else { \
        rt->inst_type##_timer_last = inst->prev; \
    } \
    if (inst->prev != NULL) { \
        inst->prev = NULL; \
        inst->next = rt->inst_type##_timer_head; \
        rt->inst_type##_timer_head->prev = inst; \
        rt->inst_type##_timer_head = inst; \
    } \
    struct timeval tv; \
    gettimeofday(&tv, NULL); \
    inst->last_update = tv.tv_sec

#endif