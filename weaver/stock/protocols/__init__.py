from weaver.stock.headers import ethernet as ethernet_header


def ethernet():
    eth = connectionless()
    eth.header = parse(ethernet_header)
    return eth
