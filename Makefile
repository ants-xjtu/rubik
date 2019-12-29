# for displaying correctly with PyCharm Makefile plugin
LANG := en_US.ISO-8859-1
# for tee >(...)
SHELL := /bin/bash

T ?= pcap
A ?= weaver_whitebox.c

bb := weaver_blackbox.c
wb := weaver_whitebox.template.c
sep = Weaver Auto-generated Blackbox Code

all: procpkts

procpkts: $(bb) $(A) native/drivers/$(T).c native/weaver.h native/runtime/libwvrt.a
	$(CC) -g -O3 -o $@ $^ -I./native -lpcap

gen:
	# https://stackoverflow.com/a/7104422
	python3 -m weaver | tee >(sed -e "/$(sep)/,\$$d" > $(wb)) | sed -n -e "/$(sep)/,\$$w $(bb)"

native/runtime/libwvrt.a:
	$(MAKE) -C native/runtime

clean:
	-$(RM) procpkts $(wb) $(bb)
	-$(RM) native/weaver.h.gch
	$(MAKE) -C native/runtime clean

.PHONY: all clean weaver_blackbox.c native/runtime/libwvrt.a
