from io import StringIO
import os
import sh
from sh import diskutil, dd, systemsetup, Command, security, defaults
from tower import osutils

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
    airport = Command('/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport')
    buf = StringIO()
    airport('-I', _out=buf)
    result = buf.getvalue()
    ssid = result.split(" SSID: ")[1].split(" ")[0].strip()

    buf = StringIO()
    security('find-generic-password', '-a', ssid , '-g', _err=buf)
    result = buf.getvalue()
    password = result.split('password: "')[1].split('"')[0]
    
    return ssid, password

def get_timezone():
    buf = StringIO()
    with sh.contrib.sudo:
        systemsetup('-gettimezone', _out=buf)
    result = buf.getvalue()
    return result.split("Time Zone:")[1].strip()

def get_keymap():
    buf = StringIO()
    defaults('read', os.path.expanduser('~/Library/Preferences/com.apple.HIToolbox.plist'), _out=buf)
    result = buf.getvalue()
    long_name = result.split('"KeyboardLayout Name" = ')[1].strip().split(";")[0].strip()
    return osutils.MACOS_NAME_TO_X11_CODE[long_name]