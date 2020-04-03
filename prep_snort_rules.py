from sys import argv
from re import search

content = bytearray()

with open(argv[1]) as rules_file:
    for rule in rules_file:
        info = {}
        for arg in search(r"\(([^\)]+)\)", rule)[1].split(";"):
            key, value = tuple(arg.split(":", 1))
            key = key.strip()
            value = value.strip()
            if key == "msg":
                info["msg"] = value[1:-1]
            elif key == "content":
                # todo
                info["content"] = value[1:-1].encode()

        def write_length_value(bs):
            length = len(bs)
            assert length < 1 << 16
            content.append(length & 0xFF00)
            content.append(length & 0x00FF)
            content.extend(bs)

        write_length_value(info["msg"].encode())
        write_length_value(info["content"])

with open("snort.bin", "wb") as bin_file:
    bin_file.write(content)
