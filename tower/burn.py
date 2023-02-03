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
from passlib.hash import sha512_crypt

from tower.configs import DEFAULT_RASPIOS_IMAGE
from tower import osutils


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


def generate_firstrun_script(params):
    with open('scripts/firstrun.sh', 'r') as f:
        template = Template(f.read())
    script = template.safe_substitute(params)
    return script


def write_image(image, device):
    start_time = time.time()
    if os.path.exists(osutils.rpi_imager_path()):
        # TODO: disable ejection
        # WIN: reg add "HKCU\Software\Raspberry Pi\Imager" /v telemetry /t REG_DWORD /d 0
        # LINUX: eject=false in ~/.config/Raspberry Pi/Imager.conf
        # MAC: defaults write org.raspberrypi.Imager.plist eject -bool NO
        rpi_imager = Command(osutils.rpi_imager_path())
        print(f"Burning {device} with rpi-imager, be patient please...")
        rpi_imager('--cli', '--debug', image, device, _out=print)
    else:
        print(f"Burning {device} with dd, be patient please...")
        osutils.dd(image, device)
    duration = time.time() - start_time
    print(f"{device} burnt in {duration}s.")


def ensure_device_is_mounted(device):
    mountpoint = osutils.get_mount_point(device)
    if mountpoint is None:
        osutils.mount(device)
        mountpoint = osutils.get_mount_point(device)
    if mountpoint is None:
        sys.exit("Error in mouting") #TODO
    return mountpoint


def prepare_first_run(mountpoint, config):
    print("Generating firstrun.sh...")

    with open(config['public-key']) as f:
        public_key = f.read()
    
    params = dict(
        HOSTNAME = f'{config["name"]}.tower',
        PUBLIC_KEY = public_key,
        LOGIN = config["default-ssh-user"],
        PASSWORD = sha512_crypt.hash(config["password"]),
        KEY_MAP = osutils.get_keymap(),
        TIME_ZONE = osutils.get_timezone(),
        ONLINE = 'true' if config["online"] else 'false',
    )
    if config["online"]:
        params.update(osutils.discover_wlan_params())

    firstrun_script = generate_firstrun_script(params)
    with open(os.path.join(mountpoint, 'firstrun.sh'), "w") as f:
        f.write(firstrun_script)
    shutil.copy('scripts/cmdline.txt', mountpoint)
    shutil.copy('scripts/dhcpcd.conf', mountpoint)


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


def update_ssh_config(computer_name, ip, user):
    config_path = os.path.join(os.path.expanduser('~'), '.ssh/config')
    shutil.copy(config_path, f'{config_path}.{datetime.now().strftime("%Y%m%d%H%M%S")}.bak')
    # TODO: check if IP or host already here
    with open(config_path, 'a') as f:
        f.write("\n")
        f.write(f"Host {computer_name}\n")
        f.write(f" HostName {ip}\n")
        f.write(f" User {user}\n")
        f.write(f" IdentityFile ~/.ssh/{computer_name}\n")
        f.write("  StrictHostKeyChecking no\n") # same IP/computer with different name should happen..
    print(f"{config_path} updated")


def burn_image(config):
    download_latest_image(config["default-raspios-image"])
    device = detect_sdcard_device() if not config['sd-card'] else config['sd-card']
    write_image(".cache/raspios.img", device)
    mountpoint = ensure_device_is_mounted(device)
    prepare_first_run(mountpoint, config)
    print(f"SD Card ready. Please insert the SD-Card in the Raspberry-PI, turn it on and wait for it to be detected on the network.")
    ip = discover_ip(config['name'])
    update_ssh_config(config['name'], ip, config['default-ssh-user'])
