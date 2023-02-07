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

from tower.configs import DEFAULT_RASPIOS_IMAGE
from tower import osutils

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


def generate_firstrun_script(config):
    print("Generating firstrun.sh...")
    params = {key.upper().replace("-", "_"): config[key] for key in config}
    with open('scripts/firstrun.sh', 'r') as f:
        template = Template(f.read())
    script = template.safe_substitute(params)
    return script


def copy_firstrun_files(device, firstrun_script):
    mountpoint = osutils.ensure_device_is_mounted(device)
    with open(os.path.join(mountpoint, 'firstrun.sh'), "w") as f:
        f.write(firstrun_script)
    shutil.copy('scripts/cmdline.txt', mountpoint)
    shutil.copy('scripts/dhcpcd.conf', mountpoint)
    # TODO: integrate this apps in the image
    shutil.copy('scripts/apt-offline-1.8.5.tar.gz', mountpoint)
    shutil.copy('scripts/apt-update-20230207.zip', mountpoint)
    shutil.copy('scripts/x2goserver-apt.zip', mountpoint)


def discover_ip(computer_name):
    buf = StringIO()
    arp('-a', _out=buf)
    result = buf.getvalue()
    lines = result.split("\n")
    for line in lines:
        if line.startswith(f'{computer_name}.local'):
            ip = line.split("(")[1].split(")")[0]
            print(f"IP found: {ip}")
            return ip
    print(f"Fail to discover the IP for {computer_name}. Retrying in 10 seconds")
    time.sleep(10)
    return discover_ip(computer_name)


def update_ssh_config(config, ip):
    config_path = os.path.join(os.path.expanduser('~'), '.ssh/config')
    shutil.copy(config_path, f'{config_path}.{datetime.now().strftime("%Y%m%d%H%M%S")}.bak')
    # TODO: check if IP or host already here
    with open(config_path, 'a') as f:
        f.write("\n")
        f.write(f"Host {config['name']}\n")
        f.write(f" HostName {ip}\n")
        f.write(f" User {config['default-ssh-user']}\n")
        f.write(f" IdentityFile {config['private-key-path']}\n")
        f.write(" StrictHostKeyChecking no\n") # same IP/computer with different name should happen..
        f.write(" LogLevel FATAL\n") # TODO: in dev mode only
    print(f"{config_path} updated")


# 1. Download image
# 2. Prepare firstrun.sh
# 3. Burn image
# 4. Copy files in sd-card
# 5. Discover IP
# 6. Update ssh config file
def burn_image(config):
    download_latest_image(config["default-raspios-image"])
    firstrun_script = generate_firstrun_script(config)
    osutils.write_image(".cache/raspios.img", config['sd-card'])
    copy_firstrun_files(config['sd-card'], firstrun_script)
    print(f"SD Card ready. Please insert the SD-Card in the Raspberry-PI, turn it on and wait for it to be detected on the network.")
    ip = discover_ip(config['name'])
    update_ssh_config(config, ip)
