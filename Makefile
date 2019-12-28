# for displaying correctly with PyCharm Makefile plugin
LANG=en_US.ISO-8859-1

all: procpkts

procpkts: weaver_blackbox.c native/driver.c native/weaver.h native/runtime/libwvrt.a
	$(CC) -g -O3 -o $@ $^ -I./native -lpcap

weaver_blackbox.c:
	python3 -m weaver > $@

native/runtime/libwvrt.a:
	$(MAKE) -C native/runtime

clean:
	-$(RM) procpkts weaver_blackbox.c
	-$(RM) native/weaver.h.gch
	$(MAKE) -C native/runtime clean

.PHONY: all clean weaver_blackbox.c native/runtime/libwvrt.a
