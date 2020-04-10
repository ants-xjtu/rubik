snort-all.o: snort.o libac/libacism.a http-parser/libhttp_parser.o
	$(LD) -r -o $@ $^ -L/usr/lib/x86_64-linux-gnu -lconfig

snort.o: snort.cxx
	$(CXX) -c -O3 -o $@ $^ -I../native

libac/libacism.a:
	$(MAKE) -C libac

http-parser/libhttp_parser.o:
	$(MAKE) -C http-parser library

clean:
	-$(MAKE) -C libac clean
	-$(MAKE) -C http-parser clean
	-$(RM) snort.o snort-all.o