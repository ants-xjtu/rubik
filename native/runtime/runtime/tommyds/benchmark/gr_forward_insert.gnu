load "gr_common.gnu"

set output bdir.tdir."img_forward_insert".bext
set title "Forward Insert".tsub
data = bdir.tdir.'dat_forward_insert.lst'

plot data using 1:2 title columnheader(2), \
	for [i=3:21] '' using 1:i title columnheader(i) ls i-1

