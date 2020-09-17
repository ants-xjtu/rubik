## Proof-of-concept and evaluation prototype for NSDI'21: *Programming Network Stack for Middleboxes with Rubik*

Step 0, make sure `python3` installed with version >= 3.7; C toolchain (e.g. `build-essential` on Ubuntu) installed; `libpcap-dev` is required for `pcap` target and DKDP SDK is required for `dkdp` target. And moka package is installed:

```
pip3 install moka
```

Step 1, generate `weaver_blackbox.c` according to configure

```
# to build stocking protocol stacks
make gen C=stock.tcp_ip
make gen C=stock.gtp
```

Step 2, compile the blackbox along with custom code

```
# auto-generated blank template
make A=weaver_whitebox.template.c
# DPDK target
make A=... T=dpdk
```

Finally, run built executable `procpkts`.

----

Non-exhuasted willing list
* properly-designed prototype-provided and stack-defined event system
* fully-implemented "strict mode & loose mode"
* ~~non-sequence instance~~
* insert-assemble-(no next & callback) optimization pattern
* foreign UInt may cause bug
* built-in events:
    * `psm.fail`
    * `seq.retrex`
    * `seq.overlap`
    * `seq.outofwindow`
    * `seq.outofbuffer`
* `stack.foo.layer.context.buffer_data` -> `stack.foo.buffer_data`
* else branch for header parsing
* timer
