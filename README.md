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
# generally it's recommend to edit the copy of the template
cp weaver_whitebox.template.c weaver_whitebox.c
# and build it with custom code
# DPDK target
make T=dpdk
```

Finally, run built executable `procpkts`.

----

Rubik is a perfect tool for:
* building software middlebox for network stacks, e.g. TCP/IP, GTP, QUIC
* validating the functionality of newly-designed protocols
* modeling network protocols/stacks with a comprehensive abstraction

To learn more, please head on to [a tour of Rubik][./doc/00-a-tour-of-rubik.markdown] and enjoy hacking!
