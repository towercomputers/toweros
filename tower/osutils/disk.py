import json
import logging
import time
from datetime import timedelta
import os
from io import StringIO
import sys

import sh
from sh import lsblk, mount as _mount, umount, dd as _dd

logger = logging.getLogger('tower')

def mount(partition):
    mountpoint = os.path.expanduser('~/tower-sd-card')
    if not os.path.exists(mountpoint):
        os.makedirs(mountpoint)
    with sh.contrib.sudo(password="", _with=True):
        _mount('-o', f'gid={os.getgid()},uid={os.getuid()}', partition, mountpoint)
    return mountpoint

def unmount_all(device):
    buf = StringIO()
    lsblk('-J', '-T', device, _out=buf)
    result = json.loads(buf.getvalue())
    for partition in result['blockdevices'][0]['children']:
        if partition['mountpoints'][0]:
            with sh.contrib.sudo(password="", _with=True):
                try:
                    umount(partition['mountpoints'][0])
                except sh.ErrorReturnCode_32: # target is busy
                    logger.debug("Unmount: device is busy. Retrying in 5 seconds.")
                    time.sleep(5)
                    umount(partition['mountpoints'][0])

def mountpoint(device, partition_index=0):
    buf = StringIO()
    lsblk('-J', '-T', device, _out=buf)
    result = json.loads(buf.getvalue())
    if partition_index < len(result['blockdevices'][0]['children']):
        partition = result['blockdevices'][0]['children'][partition_index]
        return partition['name'], partition['mountpoints'][0]
    raise OperatingSystemException(f"Invalide partition index `{partition_index}`")

def ensure_partition_is_mounted(device, partition_index=0):
    name, mountpoint_path = mountpoint(device, partition_index)
    if mountpoint_path is None:
        return mount(f"/dev/{name}")
    return mountpoint_path

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
        logger.error("sd-card not found.")
        return None
    elif (len(new_devices) > 1):
        logger.error("More than one disk found.")
        return None
    else:
        logger.info(f"sd-card found: {new_devices[0]}")
        return new_devices[0]

def write_image(image, device):
    start_time = time.time()
    logger.info(f"Burning {device} with dd, be patient please...")
    if mountpoint(device) is not None:
        unmount_all(device)
    with sh.contrib.sudo(password="", _with=True):
        #cat(image, '>', device)
        _dd(f"if={image}", f"of={device}", "bs=8M", "conv=sync", "status=progress", _out=sys.stdout)
    duration = timedelta(seconds=time.time() - start_time)
    logger.info(f"{device} burnt in {duration}.")