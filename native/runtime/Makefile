all: libwvrt.a

libwvrt.a: interface.o tommyds/tommy.o
	$(AR) rc $@ $^

%.o: %.c ../weaver.h
	$(CC) -c -g -O3 -I.. $^

clean:
	-$(RM) libwvrt.a *.o

.PHONY: all clean
