# Weaver

![](https://github.com/sgdxbc/weaver/workflows/build/badge.svg)

First, run

```
$ make gen
```

Two files named `weaver_blackbox.c` and `weaver_whitebox.template.c` will be generated. 

**Do NOT touch or read `weaver_blackbox.c`.**

Rename `weaver_whitebox.template.c` (to prevent overriding by next `make gen`) and edit it as you wish.

Run

```
$ make T=<target> A=<whitebox>
```

Set `<target>` to driver you wish to use (currently support: `pcap`), and `<whitebox>` to path to your 
edited code (defaults to `weaver_whitebox.c`).

An executable named `procpkts` will be built.

With `pcap` driver, run `procpkts` with pcap file name as argument. The packets in pcap file will be 
replayed forever, and throughput will be printed periodically. Type Ctrl-C to exit.

----

The `weaver` folder contains a Python module, with following files:
* `code.py` definitions of `Instr` (and its subclasses), `Value` (and its subclasses) and 
`BasicBlock`.
* `util.py`
* `auxiliary.py` definitions of `reg_aux`, which acts as a global symbol table for all registers, and 
`RegAux` with its subclasses, which are elements in `reg_aux`.
* `header.py` definitions of `Struct` and `ParseAction` (and its subclasses). `Struct` uses `reg_aux`
to construct information of itself.
* `writer.py` and `writer_context.py`. `writer.py` provides various kinds of `InstrWriter` and 
`ValueWriter` for `Instr`s and `Value`s to write themselves properly into specific context. 
`writer_context.py` contains `Context`s of different levels. A `GlobalContext` could write the whole
generated C program after executing all `BasicBlock`s.
* `__main__.py` command line interface.
* `stock` submodule provides pre-defined resources.

The `native` folder contains C code files which should be built along with generated code.
* `weaver.h` all-in-one universal definitions for generated code, runtime library and driver
* `runtime` platform-and-target-independent supporting data structures and functions, such as hash
table, reorder buffer, etc.
* `drivers` setup application in several environments. Each of code files in `drivers` implements an
entry point (e.g. `main` or equivalent) for application, so only one of them should be evolved in one
building process.