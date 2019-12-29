#include <stdio.h>
#include <pcap.h>
#include "weaver.h"

void proc(WV_Byte *runtime, const struct pcap_pkthdr *pcap_header, const WV_Byte *pcap_data) {
    WV_ByteSlice packet = { .cursor = pcap_data, .length = pcap_header->len };
    WV_U8 status = WV_ProcessPacket(packet, (void *)runtime);
    WV_ProfileRecord((void *)runtime, pcap_header->len, status);
}

int main(int argc, char *argv[]) {
    if (argc <= 1) {
        printf("no pcap file\n");
        return 0;
    }
    char *pcap_filename = argv[1];

    WV_Runtime runtime;
    if (WV_InitRuntime(&runtime)) {
        fprintf(stderr, "runtime initialization fail\n");
        return 1;
    }

    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *pcap_packets = pcap_open_offline(pcap_filename, errbuf);
    if (!pcap_packets) {
        fprintf(stderr, "pcap_open_offline: %s\n", errbuf);
        return 1;
    }

    WV_ProfileStart(&runtime);
    for (;;) {
        pcap_loop(pcap_packets, -1, proc, (void *)&runtime);
        pcap_close(pcap_packets);
        pcap_packets = pcap_open_offline(pcap_filename, errbuf);
    }

    if (WV_CleanRuntime(&runtime)) {
        fprintf(stderr, "runtime cleanup fail\n");
        return 1;
    }

    return 0;
}