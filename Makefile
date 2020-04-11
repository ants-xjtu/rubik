SHELL := /bin/bash


A ?= weaver_whitebox.c
T ?= pcap
C ?= stack_conf
bb := weaver_blackbox.c
wb := weaver_whitebox.template.c
sep = Weaver Auto-generated Blackbox Code

BUILD_DIR = ./build/
APP = procpkts
TARGET_FLAG = -DWV_TARGET_$(T)
export TARGET_FLAG

### GCC ###
GCC = gcc
GCC_OPT = -m64 # -Wall -DNEWEV -Werror

GCC_OPT += -g -DNETSTAT -DINFO -DDBGERR -DDBGCERR
# GCC_OPT += -O3 -DNDEBUG -DNETSTAT -DINFO -DDBGERR -DDBGCERR
GCC_OPT += $(DBG_OPT)

### LIBRARIES AND INCLUDES ###
INC_DIR = ./native
INC= -I$(INC_DIR) -I$(INC_DIR)/runtime -I$(INC_DIR)/runtime/tommyds

### SOURCE FILES ###

LIB_FLAGS += -lstdc++ -lpcre2-8
ifeq ($(T), pcap)
LIB_FLAGS += -lpcap
endif

ifeq ($(T), dpdk)
ifeq ($(RTE_SDK),)
$(error "Please define RTE_SDK environment variable")
endif
RTE_TARGET ?= x86_64-native-linuxapp-gcc

NIC ?= XL710
FWD ?= FWD
PERF ?= EVAL_PERF
SRC_DIR = $(PWD)
SRCS = $(bb) $(A) native/drivers/$(T).c $(SRC_DIR)/native/runtime/libwvrt.a
DPDK_INC = -I$(SRC_DIR)/native/ -I$(SRC_DIR)/native/runtime -I$(SRC_DIR)/native/runtime/tommyds
include $(RTE_SDK)/mk/rte.vars.mk
CFLAGS += $(DPDK_INC) -D$(NIC) -D$(PERF) $(GCC_OPT) -D$(FWD)
LDFLAGS += -lpcre2-8

SRCS-y := $(SRCS)
include $(RTE_SDK)/mk/rte.extapp.mk

$(SRC_DIR)/native/runtime/libwvrt.a:
	cd $(SRC_DIR)/native/runtime && $(MAKE) -C .

endif

ifeq ($(T), pcap)
### GOALS ###
SRCS = $(bb) $(A) native/drivers/$(T).c native/runtime/libwvrt.a

all: $(APP)

$(APP): $(SRCS)
	$(GCC) $(GCC_OPT) -o $@ $^ $(INC) $(LIBS) $(LIB_FLAGS) $(TARGET_FLAG)

native/runtime/libwvrt.a:
	$(MAKE) -C native/runtime

clean:
	-$(RM) procpkts $(wb) $(bb)
	-$(RM) -rf build/
	-$(RM) native/weaver.h.gch
	$(MAKE) -C native/runtime clean

.PHONY: all clean weaver_blackbox.c native/runtime/libwvrt.a
endif

gen:
	# https://stackoverflow.com/a/7104422
	python3.7 -m weaver $(C) | tee >(sed -e "/$(sep)/,\$$d" > $(wb)) | sed -n -e "/$(sep)/,\$$w $(bb)"
