from weaver.stock.headers import ethernet as ethernet_header
from weaver.lang import connectionless, parse


def ethernet():
    eth = connectionless()
    eth.header = parse(ethernet_header)
    return eth
