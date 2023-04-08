from sh import timedatectl, localectl

def get_timezone():
    result = timedatectl()
    return result.split("Time zone:")[1].strip().split(" ")[0].strip()

def get_keymap():
    result = localectl()
    return result.split("VC Keymap:")[1].strip().split(" ")[0].strip()

def get_lang():
    result = localectl()
    return result.split("System Locale:")[1].strip().split("LANG=")[1].split("\n")[0].strip()