#include <stdio.h>
#include "weaver.h"

int main(void) {
    printf("weaver driver\n");

    WV_Runtime runtime;
    WV_ProcessPacket(NULL, 0, &runtime);

    return 0;
}