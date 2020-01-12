class ip:
    version = Bit(4)
    header_length = Bit(4).auto << 2
    tos = Byte(1)
    total_length = U16()
    identifier = Byte(2)
    _ = Bit(1).unused
    dont_frag = Bit(1).v
    more_frag = Bit(1)
    offset_upper = Bit(5)
    offset_lower = Bit(8)
    ttl = Bit(8)
    protocol = Bit(8)
    checksum = U16()
    src_ip = Bit(32)
    dst_ip = Bit(32)

    class auto:
        offset: U16 = ip.offset_upper << 8 + ip.offset_lower
        length: U16 = ip.total_length - ip.header_length
