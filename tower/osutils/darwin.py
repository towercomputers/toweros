from io import StringIO
from sh import diskutil, dd

def get_device_list():
    buf = StringIO()
    diskutil('list', 'external', 'physical', _out=buf, _err=buf)
    return [e.split(" ")[0] for e in buf.getvalue().split("\n") if e != "" and e[0] != " "]

def mount(device):
    diskutil('mountDisk', device)

def get_mount_point(device):
    buf = StringIO()
    try:
        diskutil('info', f'{device}s1', _out=buf) # first partition readable in macos/windows
    except sh.ErrorReturnCode_1: # disk not found
        return None
    result = buf.getvalue()
    if "Mount Point:" in result:
        return result.split("Mount Point:")[1].strip().split(" ")[0].strip()
    else:
        return None

def unmount(device):
    diskutil('unmountDisk', device)

def rpi_imager_path():
    return "/Applications/Raspberry Pi Imager.app/Contents/MacOS/rpi-imager"

def dd(image, device):
    if get_mount_point(device) is not None:
        unmount(device)
    dd(f"if={image}",f"of={device}", "bs=8m", "conv=sync")

def get_wlan_infos():
    pass