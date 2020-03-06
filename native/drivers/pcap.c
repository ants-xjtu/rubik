#include <stdio.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>

#include <pcap.h>
#include <weaver.h>

WV_U8 ctrl_c = 0;

void ctrl_c_handler(int sig) {
    if (ctrl_c) {
        printf("shut down badly\n");
        exit(1);
    }
    printf("\nwill shut down (ctrl-c again to kill)\n");
    ctrl_c = 1;
}

typedef struct {
    WV_Runtime *runtime;
    pcap_t *pcap;
} PcapUser;

void proc(WV_Byte *user, const struct pcap_pkthdr *pcap_header, const WV_Byte *pcap_data) {
    WV_Runtime *runtime = ((PcapUser *)user)->runtime;
    WV_ByteSlice packet = { .cursor = pcap_data, .length = pcap_header->len };
    WV_U8 status = WV_ProcessPacket(packet, runtime);
    WV_ProfileRecord(WV_GetProfile(runtime), pcap_header->len, status);
    if (ctrl_c) {
        pcap_breakloop(((PcapUser *)user)->pcap);
    }
}

int main(int argc, char *argv[]) {
    char *pcap_filename = NULL;
    WV_U8 no_loop = 0;
    for (int i = 1; i < argc; i += 1) {
        if (strcmp(argv[i], "--noloop") == 0) {
            no_loop = 1;
        } else {
            pcap_filename = argv[i];
        }
    }
    if (pcap_filename == NULL) {
        printf("no pcap file\n");
        return 0;
    }

    WV_Runtime *runtime;
    if (!(runtime = WV_AllocRuntime())) {
        fprintf(stderr, "runtime initialization fail\n");
        return 1;
    }

    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *pcap_packets = pcap_open_offline(pcap_filename, errbuf);
    if (!pcap_packets) {
        fprintf(stderr, "pcap_open_offline: %s\n", errbuf);
        return 1;
    }

    PcapUser user = { .runtime = runtime, .pcap = pcap_packets };

    signal(SIGINT, ctrl_c_handler);
    WV_Setup();
    WV_ProfileStart(WV_GetProfile(runtime));
    for (;;) {
        pcap_loop(pcap_packets, -1, proc, (void *)&user);
        pcap_close(pcap_packets);
        if (ctrl_c || no_loop) {
            break;
        }
        pcap_packets = pcap_open_offline(pcap_filename, errbuf);
        if (!pcap_packets) {
            fprintf(stderr, "pcap_open_offline: %s\n", errbuf);
            return 1;
        }
    }

    WV_ProfileRecordPrint(WV_GetProfile(runtime));
    if (WV_FreeRuntime(runtime)) {
        fprintf(stderr, "runtime cleanup fail\n");
        return 1;
    }

    printf("shut down correctly\n");

    return 0;
}