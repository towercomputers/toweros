import os
import platform
import re
import time
import json
from io import StringIO

import requests
import sh
from sh import xz, Command

from tower.configs import DEFAULT_RASPIOS_IMAGE

def device_list():
    if platform.system() == "Darwin":
        from sh import diskutil
        buf = StringIO()
        diskutil('list', 'external', 'physical', _out=buf, _err=buf)
        return [e.split(" ")[0] for e in buf.getvalue().split("\n") if e != "" and e[0] != " "]
    elif platform.system() == "Linux":
        from sh import lsblk
        buf = StringIO()
        lsblk('-J', '-T', '-d', _out=buf)
        result = json.loads(buf.getvalue())
        return [f"/dev/{e['name']}" for e in result['blockdevices']]
    elif platform.system() == "Windows":
        return [] #TODO


def detect_sdcard_device():
    k = None
    while k is None:
        k = input("Please ensure the sd-card is *NOT* connected and press ENTER.")
    devices_before = device_list()
    
    k = None
    while k is None:
        k = input("Please insert now the sd-card and press ENTER.")

    time.sleep(2)
    devices_after = device_list()
    new_devices = list(set(devices_after) - set(devices_before))

    if (len(new_devices) == 0):
        print("sd-card not found. Please try again!")
        detect_sdcard_device()
    elif (len(new_devices) > 1):
        print("more than one sd-card found. Please try again!")
        detect_sdcard_device()
    else:
        print(f"sd-card found: {new_devices[0]}")
        return new_devices[0]


def download_latest_image():
    if not os.path.exists(".cache"):
        os.makedirs(".cache")

    if not os.path.exists(".cache/raspios.img"):
        print("Downloading image...")
        resp = requests.get(DEFAULT_RASPIOS_IMAGE)
        with open(".cache/raspios.img.xz", "wb") as f:
            f.write(resp.content)
        print("Decompressing image...")
        xz('-d', ".cache/raspios.img.xz")
    else:
        print("Using image in cache.")

    print("Image ready to burn.")


def rpi_imager_path():
    if platform.system() == "Darwin":
        return "/Applications/Raspberry Pi Imager.app/Contents/MacOS/rpi-imager"
    elif platform.system() == "Windows":
        return "rpi-image.exe" # TODO
    else:
        return "/usr/bin/rpi-imager"


def rpi_imager_installed():
    return os.path.exists(rpi_imager_path())


def rpi_imager(image, device):
    rpi_imager = Command(rpi_imager_path())
    print(f"Burning {device} with rpi-imager, be patient please...")
    rpi_imager('--cli', '--debug', image, device, _out=print)


def unmount(device):
    if platform.system() == "Darwin":
        from sh import diskutil
        diskutil('unmountDisk', device)
    elif platform.system() == "Linux":
        from sh import lsblk
        buf = StringIO()
        lsblk('-J', '-T', '-d', _out=buf)
        result = json.loads(buf.getvalue())
        mountpoint = result['blockdevices'][0]['mountpoint']
        if mountpoint not in [None, ""]:
            from sh import umount
            umount(mountpoint)


def dd(image, device):
    from sh import dd
    unmount(device)
    flag = "oflag" if platform.system() != "Darwin" else "conv"
    print(f"Burning {device} with dd, be patient please...")
    dd("if=.cache/raspios.img",f"of={device}", "bs=8m", f"{flag}=sync")


def burn_image(config):
    download_latest_image()
    device = detect_sdcard_device()
    
    start_time = time.time()
    if rpi_imager_installed():
        rpi_imager(".cache/raspios.img", device)
    else:
        dd(".cache/raspios.img", device)
    duration = time.time() - start_time

    print(f"SD Card burnt in {duration}s.")
