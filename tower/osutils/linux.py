from io import StringIO
from sh import lsblk, mount, umount

def get_device_list():
    buf = StringIO()
    lsblk('-J', '-T', '-d', _out=buf)
    result = json.loads(buf.getvalue())
    return [f"/dev/{e['name']}" for e in result['blockdevices']]

def mount(device):
    mount(device)

def get_mount_point(device):
    buf = StringIO()
    lsblk('-J', '-T', '-d', device, _out=buf)
    result = json.loads(buf.getvalue())
    return result['blockdevices'][0]['mountpoint']

def unmount(device):
    mountpoint = get_mount_point(device)
    if mountpoint not in [None, ""]:
        umount(mountpoint)

def rpi_imager_path():
    return "/usr/bin/rpi-imager"

def dd(image, device):
    if get_mount_point(device) is not None:
        unmount(device)
    dd(f"if={image}",f"of={device}", "bs=8m", "oflag=sync")

def get_wlan_information():
    pass