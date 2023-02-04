from io import StringIO
import os
import sh
from sh import diskutil, dd, Command, security, defaults, readlink
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

def disable_rpi_image_ejection():
    defaults('write', 'org.raspberrypi.Imager.plist', 'eject', '-bool', 'NO')

def dd(image, device):
    if get_mount_point(device) is not None:
        unmount(device)
    dd(f"if={image}",f"of={device}", "bs=8m", "conv=sync")

def scan_wifi_countries():
    airport = Command('/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport')
    buf = StringIO()
    airport('-s', _out=buf)
    result = buf.getvalue()

    lines = result.split("\n")
    lines.pop()
    ssid_end_pos = lines[0].find('SSID') + 4
    cc_pos = lines[0].find('CC')
    lines.pop(0)

    wifis = {}
    for line in lines:
        ssid = line[0:ssid_end_pos].strip()
        cc = line[cc_pos:cc_pos + 2]
        if ssid not in wifis or wifis[ssid] == '--':
            wifis[ssid] = cc

    return wifis

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
    readlink('/etc/localtime', _out=buf)
    result = buf.getvalue()
    return ("/").join(result.strip().split("/")[-2:])

def get_keymap():
    buf = StringIO()
    defaults('read', os.path.expanduser('~/Library/Preferences/com.apple.HIToolbox.plist'), _out=buf)
    result = buf.getvalue()
    long_name = result.split('"KeyboardLayout Name" = ')[1].strip().split(";")[0].strip()
    return osutils.MACOS_NAME_TO_X11_CODE[long_name]