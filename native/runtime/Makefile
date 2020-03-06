all: libwvrt.a

libwvrt.a: profile.o tommyds/tommy.o
	$(AR) rc $@ $^

tommyds/tommy.o:
	$(MAKE) -C tommyds

%.o: %.c %.h types.h
	$(CC) -c -g -O3 $< -I./tommyds $(TARGET_FLAG)

clean:
	-$(RM) libwvrt.a
	-$(RM) *.o *.gch
	-$(MAKE) -C tommyds clean

.PHONY: all clean
