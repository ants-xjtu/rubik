all: procpkts

procpkts: process_packet.c native/driver.c
	$(CC) -g -o $@ -I ./native $^

process_packet.c:
	python3 -m weaver > $@

clean:
	$(RM) procpkts process_packet.c

.PHONY: all clean

