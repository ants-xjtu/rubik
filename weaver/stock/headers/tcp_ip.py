from weaver.lang import Bit, Byte, Slice, U16, U32, self, LogicalByte


class ip:
    version = Bit(4)
    header_length = Bit(4)(self << 2)
    tos = Byte(1)
    total_length = U16()
    identifier = Byte(2)
    _1 = Bit(1)
    dont_frag = Bit(1)
    more_frag = Bit(1)
    offset_upper = Bit(5)
    offset_lower = Byte(1)
    ttl = Bit(8)
    protocol = Byte(1)
    checksum = U16()
    src_ip = Byte(4)
    dst_ip = Byte(4)

    offset = LogicalByte(2)(offset_upper << 8 + offset_lower)
    length = LogicalByte(2)(total_length - header_length)


class tcp:
    src_port = U16()
    dst_port = U16()
    seq_num = U32()
    ack_num = U32()
    header_length = Bit(4)
    _1 = Bit(4)
    cwr = Bit(1)
    ece = Bit(1)
    urg = Bit(1)
    ack = Bit(1)
    psh = Bit(1)
    rst = Bit(1)
    syn = Bit(1)
    fin = Bit(1)
    wnd_size = U16()
    checksum = U16()
    urg_ptr = U16()


@type_length(byte=1)
class tcp_options:
    @type(0)
    class eol:
        pass

    @type(1)
    class nop:
        pass

    @type(2)
    class mss:
        length = Byte(1)
        value = Byte(2)

    @type(3)
    class ws:
        length = Byte(1)
        value = Byte(1)

    @type(4)
    class sack_perm:
        length = Byte(1)

    @type(8)
    class ts:
        length = Byte(1)
        value = Byte(4)
        echo_reply = Byte(4)

    @type(12)
    class cc_new:
        length = Byte(1)
        value = Byte(4)

    @default
    class blank:
        length = Byte(1)
        value = Slice((length - 2) << 3)
