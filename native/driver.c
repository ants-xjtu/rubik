#include <stdio.h>
#include "weaver.h"

int main(void) {
    printf("weaver driver\n");

    WV_Runtime runtime;
    if (WV_InitRuntime(&runtime)) {
        fprintf(stderr, "runtime initialization fail\n");
        return 1;
    }

    WV_ByteSlice packet;
    WV_ProcessPacket(packet, &runtime);

    return 0;
}