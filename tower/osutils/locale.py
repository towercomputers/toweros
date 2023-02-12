from io import StringIO

from sh import timedatectl, localectl

class OperatingSystemException(Exception):
    pass

def get_timezone():
    buf = StringIO()
    timedatectl(_out=buf)
    result = buf.getvalue()
    return result.split("Time zone:")[1].strip().split(" ")[0].strip()

def get_keymap():
    buf = StringIO()
    localectl(_out=buf)
    result = buf.getvalue()
    return result.split("X11 Layout:")[1].strip().split(" ")[0].strip()