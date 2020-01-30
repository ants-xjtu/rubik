# for tee >(...)
SHELL := /bin/bash

T ?= pcap
A ?= weaver_whitebox.c
C ?= stack_conf

bb := weaver_blackbox.c
wb := weaver_whitebox.template.c
sep = Weaver Auto-generated Blackbox Code

all: procpkts

# TODO: native/weaver.h
procpkts: $(bb) $(A) native/drivers/$(T).c native/runtime/libwvrt.a
	$(CC) $(cflags) -g -o $@ $^ -I./native -I./native/runtime/tommyds -lpcap

gen:
	# https://stackoverflow.com/a/7104422
	python3 -m weaver $(C) | tee >(sed -e "/$(sep)/,\$$d" > $(wb)) | sed -n -e "/$(sep)/,\$$w $(bb)"

native/runtime/libwvrt.a:
	$(MAKE) -C native/runtime

clean:
	-$(RM) procpkts $(wb) $(bb)
	-$(RM) native/weaver.h.gch
	$(MAKE) -C native/runtime clean

.PHONY: all clean weaver_blackbox.c native/runtime/libwvrt.a
