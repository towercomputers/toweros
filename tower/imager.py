import os
import platform
import re
import time
import json
from io import StringIO
from string import Template
import sys
import shutil
import crypt
import string
from secrets import choice as randchoice
from datetime import datetime

import requests
import sh
from sh import xz, Command, arp
from sshconf import read_ssh_config, empty_ssh_config_file

from tower import configs
from tower import osutils
from tower import computers

def download_latest_image(url):
    if not os.path.exists(".cache"):
        os.makedirs(".cache")

    if not os.path.exists(".cache/raspios.img"):
        print(f"Downloading {url}...")
        resp = requests.get(url)
        with open(".cache/raspios.img.xz", "wb") as f:
            f.write(resp.content)
        print("Decompressing image...")
        xz('-d', ".cache/raspios.img.xz")
    else:
        print("Using image in cache.")

    print("Image ready to burn.")
    return ".cache/raspios.img" # TODO: real cache by url


def detect_sdcard_device():
    k = None
    while k is None:
        k = input("Please ensure the sd-card is *NOT* connected and press ENTER.")
    devices_before = osutils.get_device_list()
    
    k = None
    while k is None:
        k = input("Please insert now the sd-card and press ENTER.")

    time.sleep(2)
    devices_after = osutils.get_device_list()
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


def copy_firstrun_files(device, firstrun_script):
    mountpoint = osutils.ensure_device_is_mounted(device)
    with open(os.path.join(mountpoint, 'firstrun.sh'), "w") as f:
        f.write(firstrun_script)
    shutil.copyfile('scripts/cmdline.txt', os.path.join(mountpoint, 'cmdline.txt'))
    shutil.copyfile('scripts/dhcpcd.conf', os.path.join(mountpoint, 'dhcpcd.conf'))
    # TODO: integrate this apps in the image
    shutil.copyfile('scripts/apt-offline-1.8.5.tar.gz', os.path.join(mountpoint, 'apt-offline-1.8.5.tar.gz'))
    shutil.copyfile('scripts/apt-update-20230207.zip', os.path.join(mountpoint, 'apt-update-20230207.zip'))
    shutil.copyfile('scripts/x2goserver-apt.zip', os.path.join(mountpoint, 'x2goserver-apt.zip'))


def burn_image(image_url, device, firstrun_script):
    image_path = download_latest_image(image_url)
    osutils.write_image(image_path, device)
    copy_firstrun_files(device, firstrun_script)
    # TODO: unmount device

