from sys import argv
from re import search

content = bytearray()

with open(argv[1]) as rules_file:
    rule_count = 0
    for rule in rules_file:
        info = {}
        groups = search(
            r"(?:# )*alert (tcp|udp) \S+ (\d+|any|\$HTTP_PORTS) -> \S+ (\d+|any|\$HTTP_PORTS) \((.+)\)",
            rule,
        )
        if groups is None:
            continue
        is_tcp = int(groups[1] == "tcp")
        if groups[2] == "any":
            srcport = 0
        elif groups[2] == "$HTTP_PORTS":
            srcport = 80
        else:
            srcport = int(groups[2])
        if groups[3] == "any":
            dstport = 0
        elif groups[3] == "$HTTP_PORTS":
            dstport = 80
        else:
            dstport = int(groups[3])        
        args = groups[4].split(";")
        # print(rule)
        for arg in args:
            if ":" in arg:
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
            content.append((length & 0xFF00) >> 8)
            content.append(length & 0x00FF)
            content.extend(bs)

        if "content" in info:
            write_length_value(info["msg"].encode())
            write_length_value(info["content"])
            rule_count += 1

print("#rule:", rule_count)
with open("snort.bin", "wb") as bin_file:
    bin_file.write(content)
