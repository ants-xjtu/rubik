# Weaver

First, run

```
$ make gen
```

Two files named `weaver_blackbox.c` and `weaver_whitebox.template.c` will be generated. 

**Do NOT touch or read `weaver_blackbox.c`.**

Copy `weaver_whitebox.template.c` (to prevent overriding by next `make gen`) and edit as you wish.

Run

```
$ make T=<target> A=<whitebox>
```

Set `<target>` to driver you wish to use (currently support: `pcap`), and `<whitebox>` to path to your edited code (defaults to `weaver_whitebox.c`).

An executable named `procpkts` will be built.

With `pcap` driver, run it with pcap file name as argument. The packets in pcap file will be replayed forever, and throughput will be printed periodically. Type Ctrl-C to exit.