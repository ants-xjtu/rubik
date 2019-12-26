all: libwvrt.a

libwvrt.a: interface.o tommyds/tommy.o
	$(AR) rc $@ $^

%.o: %.c ../weaver.h
	$(CC) -c -g -I.. $^

clean:
	-$(RM) libwvrt.a *.o

.PHONY: all clean
