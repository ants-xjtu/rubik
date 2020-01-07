all: libwvrt.a

libwvrt.a: profile.o runtime.o tommyds/tommy.o
	$(AR) rc $@ $^

%.o: %.c %.h types.h
	$(CC) -c -g -O3 $<

runtime.o: table.h slice.h

clean:
	-$(RM) libwvrt.a
	-$(RM) *.o *.gch
	-$(RM) test_table test_bi_table

tests_exe: test_table test_bi_table

test_%: tests/%.c libwvrt.a
	$(CC) -o $@ -g $^ -I.

test: tests_exe
	./test_table && ./test_bi_table

.PHONY: all clean test
