import time
import os
from io import StringIO

import sh
from sh import udisksctl, lsblk


def udisk(action, partition):
    # TODO: configure thin client to not need sudo
    if action not in ["mount", "unmount"]:
        raise OperatingSystemException(f"Invald operation `{action}`")
    buf = StringIO()
    try:
        udisksctl(action, '-b', partition, '--no-user-interaction', _out=buf)
    except sh.ErrorReturnCode_1 as e:
        message = f"{e}"
        if "Not authorized to perform operation" in message:
            with sh.contrib.sudo:
                udisksctl(action, '-b', partition, '--no-user-interaction', _out=buf)
        else:
            raise(e)
    result = buf.getvalue()
    if f"{action}ed {partition}" not in result.lower():
        raise OperatingSystemException(f"Impossible to {action} {partition}")
    if action == "mount":
        return result.split(" at ")[1].strip()

def mountpoint(device, partition_index=0):
    buf = StringIO()
    lsblk('-J', '-T', device, _out=buf)
    result = json.loads(buf.getvalue())
    if partition_index < len(result['blockdevices'][0]['children']):
        partition = result['blockdevices'][0]['children'][partition_index]
        return partition['name'], partition['mountpoint']
    raise OperatingSystemException(f"Invalide partition index `{partition_index}`")

def unmount_all(device):
    buf = StringIO()
    lsblk('-J', '-T', device, _out=buf)
    result = json.loads(buf.getvalue())
    for partition in result['blockdevices'][0]['children']:
        if partition['mountpoint']:
            udisk("unmount", f"/dev/{partition['name']}")

def ensure_partition_is_mounted(device, partition_index=0):
    name, mountpoint = mountpoint(device, partition_index)
    if mountpoint is None:
        return udisk("mount", f"/dev/{name}")
    return mountpoint

def get_device_list():
    buf = StringIO()
    lsblk('-J', '-T', '-d', _out=buf)
    result = json.loads(buf.getvalue())
    return [f"/dev/{e['name']}" for e in result['blockdevices']]

def select_sdcard_device():
    k = None
    while k is None:
        k = input("Please ensure the sd-card is *NOT* connected and press ENTER.")
    devices_before = get_device_list()
    
    k = None
    while k is None:
        k = input("Please insert now the sd-card and press ENTER.")

    time.sleep(2)
    devices_after = get_device_list()
    new_devices = list(set(devices_after) - set(devices_before))

    if (len(new_devices) == 0):
        print("sd-card not found.")
        return None
    elif (len(new_devices) > 1):
        print("More than one disk found.")
        return None
    else:
        print(f"sd-card found: {new_devices[0]}")
        return new_devices[0]
