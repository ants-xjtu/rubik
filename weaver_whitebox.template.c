/* Weaver Whitebox Code Template */
#include "weaver.h"

#ifdef STRING_FINDER
#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>
#include <string.h>
#include <stdio.h>

void match_against_data(const unsigned char* data, unsigned int len);
#endif


WV_U8 check_eth_type(
  WV_U16 _10006
) {
  return 0;
}

WV_U8 dump_ip(
  WV_U8 _20017,
  WV_U16 _2001
) {
  return 0;
}

WV_U8 count_tcp_payload() {
  return 0;
}

WV_U8 handle_tcp_payload(
  WV_ByteSlice _4007,
  WV_U8 _4004,
  WV_U16 _4001,
  WV_U8 _40000,
  WV_U8 _4000
) {
#ifdef STRING_FINDER
  match_against_data(_4007.cursor, _4007.length);
#endif
  return 0;
}

#ifdef STRING_FINDER

pcre2_code *re;
char pcre_char[] = "[A-Za-z0-9]+@[A-Za-z0-9]+";
char string_char[] = "XUekmByX4F";


void init_pcre()
{
  int errornumber;
  PCRE2_SIZE erroroffset;
  PCRE2_SPTR pcre_pattern = (PCRE2_SPTR)pcre_char;

  re = pcre2_compile(
    pcre_pattern,  /* the pattern */
    PCRE2_DOTALL,  /* */
    0,             /* default options  */
    &errornumber,  /* for error number */
    &erroroffset,  /* for error offset */
    NULL);         /* use default compile context */

  if (re == NULL)
  {
    PCRE2_UCHAR buffer[256];
    pcre2_get_error_message(errornumber, buffer, sizeof(buffer));
    printf("PCRE2 compilation failed at offset %d: %s\n", (int)erroroffset,
      buffer);
    exit (1);
  }

}

void match_against_data(const unsigned char* data, unsigned int len)
{
  if (len == 0) return;
  int rc = 0;
  PCRE2_SPTR subject = (PCRE2_SPTR)data;
  size_t subject_length = len;

  int i = 0;
  for (; i<50; i++) {
    pcre2_match_data* match_data = pcre2_match_data_create_from_pattern(re, NULL);
    int workspaces[10];

    rc = pcre2_dfa_match(
      re, 
      subject,
      subject_length,
      0,
      PCRE2_DFA_RESTART | PCRE2_PARTIAL_SOFT,
      match_data,
      NULL,
      workspaces,
      10);

    // rc = pcre2_match(
    //   re,                   /* the compiled pattern */
    //   subject,              /* the subject string */
    //   subject_length,       /* the length of the subject */
    //   0,                    /* start at offset 0 in the subject */
    //   0,                    /* default options */
    //   match_data,           /* block for storing the result */
    //   NULL);                /* use default match context */

    pcre2_match_data_free(match_data);   /* Release memory used for the match */
  }
}

#endif