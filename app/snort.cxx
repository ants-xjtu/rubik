#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>

extern "C" {
#include "http-parser/http_parser.h"
#include "libac/acism.h"
#include <libconfig.h>
#include <pcre.h>
#include <runtime/types.h>
}

#ifdef NDEBUG
#undef assert
#define assert(x) x
#endif

ACISM *raw_ac;

struct Packet {
  WV_ByteSlice sdu;
  WV_U16 srcport;
  WV_U16 dstport;
  WV_U8 is_req;
  WV_ByteSlice uri;
};

class RuleChecker {
public:
  virtual WV_U8 check(Packet &packet) = 0;
  RuleChecker *next;
};

struct Rule {
  WV_ByteSlice message;
  RuleChecker *checker_head;
};
Rule raw_rules[2048], http_rules[2048];
WV_U16 raw_count, http_count;

class CheckSrcPort : public RuleChecker {
  WV_U16 srcport;

public:
  CheckSrcPort(WV_U16 srcport) : srcport(srcport) {}
  virtual WV_U8 check(Packet &packet) { return packet.srcport == srcport; }
};

class CheckDstPort : public RuleChecker {
  WV_U16 dstport;

public:
  CheckDstPort(WV_U16 dstport) : dstport(dstport) {}
  virtual WV_U8 check(Packet &packet) { return packet.dstport == dstport; }
};

class CheckUri : public RuleChecker {
  const char *pattern;

public:
  CheckUri(const char *pattern) : pattern(pattern) {}
  virtual WV_U8 check(Packet &packet) {
    if (packet.uri.length > 512 - 1) {
      return 0;
    }
    char buffer[512];
    memcpy(buffer, packet.uri.cursor, packet.uri.length);
    buffer[packet.uri.length] = 0;
    return strstr(buffer, pattern) != NULL;
  }
};

WV_ByteSlice clone_slice(const WV_Byte *cursor, WV_U32 length) {
  WV_ByteSlice slice = {.cursor = new WV_Byte[length], .length = length};
  memcpy((WV_Any)slice.cursor, cursor, length);
  return slice;
}

WV_ByteSlice clone_slice(const char *cursor, WV_U32 length) {
  return clone_slice(reinterpret_cast<const WV_Byte *>(cursor), length);
}

WV_ByteSlice create_slice(const char *cursor, size_t length) {
  return (WV_ByteSlice){.cursor = reinterpret_cast<const WV_Byte *>(cursor),
                        .length = static_cast<WV_U32>(length)};
}

WV_U8 add_checker(Rule &rule, RuleChecker *checker) {
  checker->next = rule.checker_head;
  rule.checker_head = checker;
  return 0;
}

WV_U8 parse_options(Rule &rule, config_setting_t *settings) {
  const char *message;
  assert(config_setting_lookup_string(settings, "msg", &message));
  WV_U32 message_length = strlen(message);
  rule.message = (WV_ByteSlice){
      .cursor = new WV_Byte[message_length],
      .length = message_length,
  };
  memcpy((WV_Any)rule.message.cursor, message, message_length);

  rule.checker_head = NULL;

  int srcport, dstport;
  assert(config_setting_lookup_int(settings, "srcport", &srcport));
  assert(config_setting_lookup_int(settings, "dstport", &dstport));
  if (srcport != 0) {
    add_checker(rule, new CheckSrcPort(srcport));
  }
  if (dstport != 0) {
    add_checker(rule, new CheckDstPort(dstport));
  }
  const char *uri_pattern;
  int uri_pattern_length;
  assert(config_setting_lookup_string(settings, "uri", &uri_pattern));
  assert(
      config_setting_lookup_int(settings, "uri_length", &uri_pattern_length));
  if (uri_pattern_length != 0) {
    char *cloned_uri = new char[uri_pattern_length + 1];
    memcpy(cloned_uri, uri_pattern, uri_pattern_length);
    cloned_uri[uri_pattern_length] = 0;
    add_checker(rule, new CheckUri(cloned_uri));
  }
  return 0;
}

extern "C" WV_U8 WV_Setup() {
  printf("[setup] read configure\n");
  config_t config;
  config_init(&config);
  assert(config_read_file(&config, "snort.cfg") == CONFIG_TRUE);

  config_setting_t *raw_settings = config_lookup(&config, "raw");
  raw_count = config_setting_length(raw_settings);
  assert(raw_count < 2048);
  MEMREF raw_strv[2048];
  for (WV_U32 i = 0; i < raw_count; i += 1) {
    config_setting_t *rule = config_setting_get_elem(raw_settings, i);
    const char *pattern;
    int pattern_length;
    assert(config_setting_lookup_string(rule, "content", &pattern));
    assert(config_setting_lookup_int(rule, "content_length", &pattern_length));
    assert(pattern_length != 0);
    raw_strv[i] =
        (MEMREF){.ptr = pattern, .len = static_cast<size_t>(pattern_length)};
    parse_options(raw_rules[i], rule);
  }

  config_setting_t *http_settings = config_lookup(&config, "http");
  http_count = config_setting_length(http_settings);
  assert(http_count < 2048);
  for (WV_U32 i = 0; i < http_count; i += 1) {
    config_setting_t *rule = config_setting_get_elem(http_settings, i);
    parse_options(http_rules[i], rule);
  }

  printf("[setup] build ac (count: %u)\n", raw_count);
  raw_ac = acism_create(raw_strv, raw_count);

  printf("[setup] finishing\n");
  config_destroy(&config);

  return 0;
}

struct UserData {
  WV_Byte active_raw[256];
  WV_Byte alerted_raw[256];
  WV_Byte alerted_http[256];
  int raw_ac_state;
  http_parser *parser;
  WV_U8 parse_end;
};

struct HTTPData {
  Packet &packet;
  UserData &user;
  HTTPData(Packet &packet, UserData &user) : packet(packet), user(user) {}
};

const WV_U8 masks[] = {
    0b10000000, 0b01000000, 0b00100000, 0b00010000,
    0b00001000, 0b00000100, 0b00000010, 0b00000001,
};

#define set_bit(bitmap, index) bitmap[index / 8] |= masks[index % 8]
#define has_bit(bitmap, index) (bitmap[index / 8] & masks[index % 8])
#define clear_bit(bitmap, index) bitmap[index / 8] &= ~masks[index % 8]

int on_match(int strnum, int textpos, WV_Any context) {
  UserData *user_data = static_cast<UserData *>(context);
  if (!has_bit(user_data->alerted_raw, strnum)) {
    set_bit(user_data->active_raw, strnum);
  }
  return 0;
}

int on_uri(http_parser *parser, const char *at, size_t length) {
  ((HTTPData *)parser->data)->packet.uri = create_slice(at, length);
  return 0;
}

int on_header_end(http_parser *parser) {
  ((HTTPData *)parser->data)->user.parse_end = 1;
  return 0;
}

typedef struct {
  WV_U16 _201;       // report_status.srcport
  WV_U16 _202;       // report_status.dstport
  WV_U8 _203;        // report_status.state
  WV_U8 _204;        // report_status.is_request
  WV_ByteSlice _205; // report_status.content
} __attribute__((packed)) H11;

extern "C" WV_U8 report_status(H11 *args, WV_Any *context) {
  WV_U8 state = args->_203;
  Packet packet = {
      .sdu = args->_205,
      .srcport = args->_201,
      .dstport = args->_202,
      .is_req = args->_204,
      .uri = WV_EMPTY,
  };

  // printf("state: %u len(content): %u\n", state, packet.sdu.length);
  if (packet.sdu.length == 0) {
    return 0;
  }

  UserData *user_data;
  if (*context == NULL) {
    *context = user_data = new UserData;
    // printf("[report] setup user data\n");
    user_data = static_cast<UserData *>(*context);
    user_data->raw_ac_state = 0;
    user_data->parser = new http_parser;
    http_parser_init(user_data->parser,
                     packet.is_req ? HTTP_REQUEST : HTTP_RESPONSE);
    user_data->parse_end = 0;
    memset(user_data->active_raw, 0, sizeof(WV_Byte) * 256);
    memset(user_data->alerted_raw, 0, sizeof(WV_Byte) * 256);
    memset(user_data->alerted_http, 0, sizeof(WV_Byte) * 256);
  }
  user_data = static_cast<UserData *>(*context);
  MEMREF text = {.ptr = reinterpret_cast<const char *>(packet.sdu.cursor),
                 .len = packet.sdu.length};
  acism_more(raw_ac, text, on_match, user_data, &user_data->raw_ac_state);
  if (!user_data->parse_end) {
    HTTPData data(packet, *user_data);
    user_data->parser->data = &data;
    http_parser_settings settings;
    memset(&settings, 0, sizeof(settings));
    settings.on_url = on_uri;
    settings.on_headers_complete = on_header_end;
    size_t nparsed = http_parser_execute(
        user_data->parser, &settings,
        reinterpret_cast<const char *>(packet.sdu.cursor), packet.sdu.length);
    if (nparsed != packet.sdu.length) {
      user_data->parse_end = 1;
    }
  }

  for (WV_U16 i = 0; i < raw_count; i += 1) {
    if (has_bit(user_data->active_raw, i)) {
      WV_U8 pass = 1;
      for (RuleChecker *checker = raw_rules[i].checker_head; checker != NULL;
           checker = checker->next) {
        if (!checker->check(packet)) {
          pass = 0;
          break;
        }
      }
      if (pass) {
        printf("[match] %*s\n", raw_rules[i].message.length,
               raw_rules[i].message.cursor);
        clear_bit(user_data->active_raw, i);
        set_bit(user_data->alerted_raw, i);
      }
    }
  }

  for (WV_U16 i = 0; i < http_count; i += 1) {
    if (!has_bit(user_data->alerted_http, i)) {
      WV_U8 pass = 1;
      for (RuleChecker *checker = http_rules[i].checker_head; checker != NULL;
           checker = checker->next) {
        if (!checker->check(packet)) {
          pass = 0;
          break;
        }
      }
      if (pass) {
        printf("[match] %*s\n", http_rules[i].message.length,
               http_rules[i].message.cursor);
        set_bit(user_data->alerted_http, i);
      }
    }
  }

  if (state == 7) {
    delete user_data->parser;
    delete user_data;
    *context = NULL;
  }

  return 0;
}
