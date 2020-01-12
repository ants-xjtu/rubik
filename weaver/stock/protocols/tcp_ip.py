from weaver.stock.headers import ip as ip_header


def ip():
    ip = connectionless()
    ip.header = parse(ip_header)
    ip.instkey([ip.header.src_ip, ip.header.dst_ip])
    ip.seq(ip.header.offset, ip.payload[:ip.header.length])
    # ...