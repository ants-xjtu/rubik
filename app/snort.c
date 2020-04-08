#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "http-parser/http_parser.h"
#include "libac/acism.h"
#include <libconfig.h>
#include <weaver.h>

#ifdef NDEBUG
#undef assert
#define assert(x) x
#endif

ACISM *raw_ac, *http_ac;
struct {
    WV_ByteSlice message;
    WV_U16 srcport;
    WV_U16 dstport;
    WV_ByteSlice uri;
} raw_rules[2048], http_rules[2048];
WV_U16 raw_count;

WV_U8 WV_Setup()
{
    printf("[setup] read configure\n");
    config_t config;
    config_init(&config);
    assert(config_read_file(&config, "snort.cfg") == CONFIG_TRUE);

    config_setting_t* raw_settings = config_lookup(&config, "raw");
    raw_count = config_setting_length(raw_settings);
    assert(raw_count < 2048);
    MEMREF raw_strv[2048];
    for (WV_U32 i = 0; i < raw_count; i += 1) {
        config_setting_t* rule = config_setting_get_elem(raw_settings, i);
        const char* pattern;
        int pattern_length;
        assert(config_setting_lookup_string(rule, "content", &pattern));
        assert(config_setting_lookup_int(rule, "content_length", &pattern_length));
        assert(pattern_length != 0);
        raw_strv[i] = (MEMREF) { .ptr = pattern, .len = pattern_length };

        const char* message;
        assert(config_setting_lookup_string(rule, "msg", &message));
        WV_U32 message_length = strlen(message);
        raw_rules[i].message = (WV_ByteSlice) {
            .cursor = malloc(sizeof(WV_Byte) * message_length),
            .length = message_length,
        };
        int srcport, dstport;
        assert(config_setting_lookup_int(rule, "srcport", &srcport));
        assert(config_setting_lookup_int(rule, "dstport", &dstport));
        raw_rules[i].srcport = srcport;
        raw_rules[i].dstport = dstport;
        memcpy((WV_Any)raw_rules[i].message.cursor, message, message_length);
    }

    printf("[setup] build raw ac (count: %u)\n", raw_count);
    raw_ac = acism_create(raw_strv, raw_count);

    printf("[setup] finishing\n");
    config_destroy(&config);

    return 0;
}

typedef struct {
    WV_U16 _201; // report_status.srcport
    WV_U16 _202; // report_status.dstport
    WV_U8 _203; // report_status.state
    WV_ByteSlice _204; // report_status.content
} __attribute__((packed)) H11;

typedef struct {
    WV_Byte active_raw[256];
    WV_Byte alerted_raw[256];
    int raw_ac_state;
} UserData;

const WV_U8 masks[] = {
    0b10000000,
    0b01000000,
    0b00100000,
    0b00010000,
    0b00001000,
    0b00000100,
    0b00000010,
    0b00000001,
};

#define set_bit(bitmap, index) bitmap[index / 8] |= masks[index % 8]
#define has_bit(bitmap, index) (bitmap[index / 8] & masks[index % 8])
#define clear_bit(bitmap, index) bitmap[index / 8] &= ~masks[index % 8]

int on_match(int strnum, int textpos, WV_Any context)
{
    UserData* user_data = context;
    if (!has_bit(user_data->alerted_raw, strnum)) {
        set_bit(user_data->active_raw, strnum);
    }
    return 0;
}

WV_U8 report_status(H11* args, WV_Any* context)
{
    WV_U8 state = args->_203;
    WV_ByteSlice sdu = args->_204;
    WV_U16 srcport = args->_201;
    WV_U16 dstport = args->_202;

    // printf("state: %u len(content): %u\n", state, sdu.length);

    if (sdu.length == 0) {
        return 0;
    }

    UserData* user_data;
    if (*context == NULL) {
        *context = malloc(sizeof(UserData));
        printf("[report] setup user data\n");
        user_data = *context;
        user_data->raw_ac_state = 0;
        memset(user_data->active_raw, 0, sizeof(WV_Byte) * 256);
        memset(user_data->alerted_raw, 0, sizeof(WV_Byte) * 256);
    }
    user_data = *context;
    MEMREF text = { .ptr = sdu.cursor, .len = sdu.length };
    acism_more(raw_ac, text, on_match, user_data, &user_data->raw_ac_state);

    for (WV_U16 i = 0; i < raw_count; i += 1) {
        if (has_bit(user_data->active_raw, i)) {
            // printf("rule %u -> %u pkt %u -> %u\n", raw_rules[i].srcport, raw_rules[i].dstport, srcport, dstport);
            if (
                (raw_rules[i].srcport == 0 || srcport == raw_rules[i].srcport) && 
                (raw_rules[i].dstport == 0 || dstport == raw_rules[i].dstport)) {
                printf("[match] %*s\n", raw_rules[i].message.length, raw_rules[i].message.cursor);
                clear_bit(user_data->active_raw, i);
                set_bit(user_data->alerted_raw, i);
            }
        }
    }

    return 0;
}
