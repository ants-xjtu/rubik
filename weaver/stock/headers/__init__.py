class ethernet:
    src_mac1 = Byte(2)
    src_mac2 = Byte(2)
    src_mac3 = Byte(2)
    dst_mac1 = Byte(2)
    dst_mac2 = Byte(2)
    dst_mac3 = Byte(2)
    protocol = U16()
