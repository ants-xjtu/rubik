from sys import argv
from re import search
from libconf import dump

content = bytearray()

with open(argv[1]) as rules_file:
    info_list = []
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
        info["srcport"] = srcport
        info["dstport"] = dstport

        args = groups[4].split(";")
        expect_uri = False
        for arg in args:
            if ":" in arg:
                key, value = tuple(arg.split(":", 1))
                key = key.strip()
                value = value.strip().split(",")[0]  # ignore modifiers
                if key == "msg":
                    info["msg"] = value[1:-1]
                elif key == "content":
                    content = ""
                    for i, part in enumerate(value[1:-1].split("|")):
                        if i % 2 == 0:
                            content += part
                        else:
                            for code in part.split(" "):
                                content += chr(int(code, 16))
                    if expect_uri:
                        info["uri_content"] = content
                        expect_uri = False
                    else:
                        info["content"] = content
            else:
                if arg.strip() == "http_uri":
                    expect_uri = True

        def write_length_value(bs):
            length = len(bs)
            assert length < 1 << 16
            content.append((length & 0xFF00) >> 8)
            content.append(length & 0x00FF)
            content.extend(bs)

        if "content" not in info:
            info["content"] = ""
        if "uri_content" not in info:
            info["uri_content"] = ""
        info_list.append(info)

print("#rule:", len(info_list))
with open("snort.cfg", "w") as cfg_file:
    dump({"rules": tuple(info_list)}, cfg_file)
