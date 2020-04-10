from sys import argv
from re import search
from libconf import dump

content = bytearray()

with open(argv[1]) as rules_file:
    info_list = []
    http_info_list = []
    pcre_count = 0
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

                # below only works for value surrounded by ""
                if value.startswith("\""):
                    raw_value = value.strip()
                    value = ""
                    for value_part in raw_value[1:].split("\""):
                        value += value_part
                        if value_part.endswith("\\"):
                            value += "\""
                        else:
                            break
                if key == "msg":
                    info["msg"] = value
                elif key == "content":
                    content = ""
                    for i, part in enumerate(value.split("|")):
                        if i % 2 == 0:
                            content += part
                        else:
                            for code in part.split(" "):
                                content += chr(int(code, 16))
                    if expect_uri:
                        # assert "uri" not in info
                        info["uri"] = content
                        expect_uri = False
                    else:
                        if "content" not in info:
                            info["content"] = content
                elif key == "pcre":
                    # print(value)
                    regex = value[1:]
                    info['pcre'], flags = tuple(regex.rsplit('/', 1))
                    info['pcre_m'] = 'm' in flags
                    info['pcre_i'] = 'i' in flags
                    info['pcre_s'] = 's' in flags
                    info['pcre_x'] = 'x' in flags
                    pcre_count += 1
            else:
                if arg.strip() == "http_uri":
                    expect_uri = True

        if "uri" not in info:
            info["uri"] = ""
        info["uri_length"] = len(info["uri"])

        if "content" in info:
            assert info["content"] != ""
            info["content_length"] = len(info["content"])
            info_list.append(info)
        else:
            http_info_list.append(info)

print("#raw:", len(info_list))
print("#http:", len(http_info_list))
print("#pcre:", pcre_count)
with open("snort.cfg", "w") as cfg_file:
    dump({"raw": tuple(info_list), "http": tuple(http_info_list)}, cfg_file)
