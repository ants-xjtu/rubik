#include <stdio.h>
#include <pcap.h>
#include "weaver.h"

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

    struct pcap_pkthdr *pcap_header;
    const WV_Byte *pcap_data;
    WV_U32 packet_count = 0;
    while (pcap_next_ex(pcap_packets, &pcap_header, &pcap_data)) {
        WV_ByteSlice packet = { .cursor = pcap_data, .length = pcap_header->len };
        WV_ProcessPacket(packet, &runtime);
        packet_count += 1;
        if (packet_count % 100000 == 0) {
            printf(".");
        }
    }
    printf("\n");

    pcap_close(pcap_packets);

    if (WV_CleanRuntime(&runtime)) {
        fprintf(stderr, "runtime cleanup fail\n");
        return 1;
    }

    return 0;
}