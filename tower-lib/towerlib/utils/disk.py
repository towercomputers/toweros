import json
import logging
import time
import os
import tempfile
import uuid

from towerlib.utils.shell import lsblk, umount, ErrorReturnCode, doas, Command
from towerlib.utils.decorators import clitask

logger = logging.getLogger('tower')

TMP_DIR = tempfile.gettempdir()

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
        logger.error("%s device not found.", device_name)
        return None
    if len(new_devices) > 1:
        logger.error("More than one disk found.")
        return None
    logger.info("%s device found: %s", device_name, new_devices[0])
    return new_devices[0]


def select_boot_device():
    return select_device("boot")


def select_install_device():
    return select_device("install")


def sh_cmd(cmd, **kwargs):
    return Command('sh')('-c', cmd, **kwargs)

def folder_to_image(folder, image_path):
    out = {"_out": logger.debug, "_err_to_out": True}
    sh_cmd(f"sync {folder}")
    get_size_cmd = f"du -L -k -s {folder} | awk '{{print $1 + 16384}}'"
    image_size = int(sh_cmd(get_size_cmd))
    sh_cmd(f"dd if=/dev/zero of={image_path} bs=1M count={image_size // 1024}")
    sh_cmd(f"mformat -i {image_path} -N 0 ::", **out)
    sh_cmd(f"mcopy -s -i {image_path} {folder}/* {folder}/.alpine-release ::", **out)
    sh_cmd(f"pigz -v -f -9 {image_path}", **out)

@clitask("Converting archive {} to image disk...")
def targz_to_image(targz_path, image_path):
    tmp_folder = f"/{TMP_DIR}/tower-build-{uuid.uuid4()}"
    sh_cmd(f"mkdir -p {tmp_folder}")
    sh_cmd(f"tar -xpf {targz_path} -C {tmp_folder}")
    folder_to_image(tmp_folder, image_path)
    sh_cmd(f"rm -rf {tmp_folder}")
