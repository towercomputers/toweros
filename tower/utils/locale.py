from sh import ls, cat, locale as getlocale

def get_timezone():
    zone = ls('--color=no', '/etc/zoneinfo/').strip()
    area = ls('--color=no', f"/etc/zoneinfo/{zone}").strip()
    return f"{zone}/{area}"

def get_keymap():
    for line in cat("/etc/conf.d/loadkmap", _iter=True):
        if line.startswith("KEYMAP="):
            keymap_name = line.split("=")[1].strip().split("/").pop().strip()
            keymap = keymap_name.split(".")[0]
            result = keymap.split("-")
            if len(result) == 1:
                result.append(keymap)
            return result
    return None

def get_lang():
    for line in getlocale(_iter=True):
        if line.startswith("LANG="):
            return line.split("=")[1].strip()
    return None
