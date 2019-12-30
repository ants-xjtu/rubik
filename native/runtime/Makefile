all: libwvrt.a

libwvrt.a: profile.o runtime.o tommyds/tommy.o
	$(AR) rc $@ $^

%.o: %.c %.h types.h
	$(CC) -c -g -O3 $<

runtime.o: table.h slice.h

clean:
	-$(RM) libwvrt.a *.o *.gch

.PHONY: all clean
