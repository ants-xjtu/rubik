from weaver.stock.headers.tcp_ip import ip as ip_header
from weaver.lang import connectionless, parse


def ip():
    ip = connectionless()
    ip.header = parse(ip_header)
    ip.key = [ip.header.src_ip, ip.header.dst_ip]
    # ip.seq(ip.header.offset, ip.payload[:ip.header.length])
    # ...