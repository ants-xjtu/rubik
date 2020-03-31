Step 1, generate `weaver_blackbox.c` according to configure

```
# to build stocking protocol stacks
make gen C=stock.tcp_ip
make gen C=stock.gtp
# to build application
make gen C=app.snort
```

Step 2, compile the blackbox along with custom code

```
# auto-generated blank template
make A=weaver_whitebox.template.c
# snort application
make A=app/snort.c
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