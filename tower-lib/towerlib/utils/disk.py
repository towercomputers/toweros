import json
import logging
import time
from datetime import timedelta
import os

import sh
from sh import lsblk, umount, ErrorReturnCode

logger = logging.getLogger('tower')

def unmount_all(device):
    result = lsblk('-J', '-T', device)
    result = json.loads(str(result))
    if not 'children' in result['blockdevices'][0]:
        return
    for partition in result['blockdevices'][0]['children']:
        if partition['mountpoints'][0]:
            with sh.contrib.sudo(password="", _with=True):
                umount(partition['mountpoints'][0])

def lazy_umount(path, retry=0):
    if not os.path.exists(path):
        return
    try:
        umount('-l', path, _out=logger.debug)
    except ErrorReturnCode:
        pass

def get_device_list():
    result = lsblk('-J', '-T', '-d')
    result = json.loads(str(result))
    return [f"/dev/{e['name']}" for e in result['blockdevices'] if e['size'] != '0B']

def select_boot_device():
    k = None
    while k is None:
        k = input("Please ensure the boot device is *NOT* connected to the Thin Client and press ENTER.")
    devices_before = get_device_list()
    
    k = None
    while k is None:
        k = input("Please insert now the boot device to the Thin Client and press ENTER.")

    time.sleep(2)
    devices_after = get_device_list()
    new_devices = list(set(devices_after) - set(devices_before))

    if (len(new_devices) == 0):
        logger.error("boot device not found.")
        return None
    elif (len(new_devices) > 1):
        logger.error("More than one disk found.")
        return None
    else:
        logger.info(f"boot device found: {new_devices[0]}")
        return new_devices[0]
