import json
import logging
import time
import os

from towerlib.utils.shell import lsblk, umount, ErrorReturnCode, doas

logger = logging.getLogger('tower')


def unmount_all(device):
    result = lsblk('-J', '-T', device)
    result = json.loads(str(result))
    if 'children' not in result['blockdevices'][0]:
        return
    for partition in result['blockdevices'][0]['children']:
        if partition['mountpoints'][0]:
            with doas:
                umount(partition['mountpoints'][0])


def lazy_umount(path):
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


def select_device(device_name):
    k = None
    while k is None:
        k = input(f"Please be sure the {device_name} device is *NOT* connected to the thin client and press \"Enter\".")
    devices_before = get_device_list()

    k = None
    while k is None:
        k = input(f"Please insert the {device_name} device into the thin client and press \"Enter\".")

    time.sleep(2)
    devices_after = get_device_list()
    new_devices = list(set(devices_after) - set(devices_before))

    if len(new_devices) == 0:
        logger.error(f"{device_name} device not found.")
        return None
    if len(new_devices) > 1:
        logger.error("More than one disk found.")
        return None
    logger.info(f"{device_name} device found: %s", new_devices[0])
    return new_devices[0]


def select_boot_device():
    return select_device("boot")


def select_install_device():
    return select_device("install")