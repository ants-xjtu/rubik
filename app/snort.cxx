#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>

extern "C" {
#include "http-parser/http_parser.h"
#include "libac/acism.h"
#include <libconfig.h>
#include <runtime/types.h>
}

#ifdef NDEBUG
#undef assert
#define assert(x) x
#endif

ACISM* raw_ac;

struct Packet {
    WV_ByteSlice sdu;
    WV_U16 srcport;
    WV_U16 dstport;
};

class RuleChecker {
public:
    virtual WV_U8 check(Packet& packet) = 0;
    RuleChecker* next;
};

struct Rule {
    WV_ByteSlice message;
    RuleChecker* checker_head;
};
Rule raw_rules[2048], http_rules[2048];
WV_U16 raw_count, http_count;

class CheckSrcPort : public RuleChecker {
    WV_U16 srcport;

public:
    CheckSrcPort(WV_U16 srcport)
        : srcport(srcport)
    {
    }
    virtual WV_U8 check(Packet& packet)
    {
        return packet.srcport == srcport;
    }
};

class CheckDstPort : public RuleChecker {
    WV_U16 dstport;

public:
    CheckDstPort(WV_U16 dstport)
        : dstport(dstport)
    {
    }
    virtual WV_U8 check(Packet& packet)
    {
        return packet.dstport == dstport;
    }
};

class CheckUri : public RuleChecker {
    WV_ByteSlice pattern;

public:
    CheckUri(WV_ByteSlice pattern)
        : pattern(pattern)
    {
    }
    virtual WV_U8 check(Packet& packet)
    {
        return 1;
    }
};

WV_ByteSlice clone_slice(const WV_Byte* cursor, WV_U32 length)
{
    WV_ByteSlice slice = { .cursor = new WV_Byte[length], .length = length };
    memcpy((WV_Any)slice.cursor, cursor, length);
    return slice;
}

WV_ByteSlice clone_slice(const char* cursor, WV_U32 length)
{
    return clone_slice(reinterpret_cast<const WV_Byte*>(cursor), length);
}

WV_U8 add_checker(Rule& rule, RuleChecker* checker)
{
    checker->next = rule.checker_head;
    rule.checker_head = checker;
    return 0;
}

extern "C" WV_U8 WV_Setup()
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
        raw_strv[i] = (MEMREF) { .ptr = pattern, .len = static_cast<size_t>(pattern_length) };

        const char* message;
        assert(config_setting_lookup_string(rule, "msg", &message));
        WV_U32 message_length = strlen(message);
        raw_rules[i].message = (WV_ByteSlice) {
            .cursor = new WV_Byte[message_length],
            .length = message_length,
        };
        memcpy((WV_Any)raw_rules[i].message.cursor, message, message_length);

        raw_rules[i].checker_head = NULL;

        int srcport, dstport;
        assert(config_setting_lookup_int(rule, "srcport", &srcport));
        assert(config_setting_lookup_int(rule, "dstport", &dstport));
        if (srcport != 0) {
            add_checker(raw_rules[i], new CheckSrcPort(srcport));
        }
        if (dstport != 0) {
            add_checker(raw_rules[i], new CheckDstPort(dstport));
        }
        const char* uri_pattern;
        int uri_pattern_length;
        assert(config_setting_lookup_string(rule, "uri", &uri_pattern));
        assert(config_setting_lookup_int(rule, "uri_length", &uri_pattern_length));
        if (uri_pattern_length != 0) {
            add_checker(raw_rules[i], new CheckUri(clone_slice(uri_pattern, uri_pattern_length)));
        }
    }

    config_setting_t* http_settings = config_lookup(&config, "http");
    http_count = config_setting_length(http_settings);
    assert(http_count < 2048);

    printf("[setup] build ac (count: %u)\n", raw_count);
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
    UserData* user_data = static_cast<UserData*>(context);
    if (!has_bit(user_data->alerted_raw, strnum)) {
        set_bit(user_data->active_raw, strnum);
    }
    return 0;
}

extern "C" WV_U8 report_status(H11* args, WV_Any* context)
{
    WV_U8 state = args->_203;
    Packet packet = { .sdu = args->_204, .srcport = args->_201, .dstport = args->_202 };

    // printf("state: %u len(content): %u\n", state, sdu.length);

    if (packet.sdu.length == 0) {
        return 0;
    }

    UserData* user_data;
    if (*context == NULL) {
        *context = user_data = new UserData;
        printf("[report] setup user data\n");
        user_data = static_cast<UserData*>(*context);
        user_data->raw_ac_state = 0;
        memset(user_data->active_raw, 0, sizeof(WV_Byte) * 256);
        memset(user_data->alerted_raw, 0, sizeof(WV_Byte) * 256);
    }
    user_data = static_cast<UserData*>(*context);
    MEMREF text = { .ptr = reinterpret_cast<const char*>(packet.sdu.cursor), .len = packet.sdu.length };
    acism_more(raw_ac, text, on_match, user_data, &user_data->raw_ac_state);

    for (WV_U16 i = 0; i < raw_count; i += 1) {
        if (has_bit(user_data->active_raw, i)) {
            WV_U8 pass = 1;
            for (RuleChecker* checker = raw_rules[i].checker_head; checker != NULL; checker = checker->next) {
                if (!checker->check(packet)) {
                    pass = 0;
                    break;
                }
            }
            if (pass) {
                printf("[match] %*s\n", raw_rules[i].message.length, raw_rules[i].message.cursor);
                clear_bit(user_data->active_raw, i);
                set_bit(user_data->alerted_raw, i);
            }
        }
    }

    if (state == 7) {
        delete user_data;
        *context = NULL;
    }

    return 0;
}
