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

from tower.configs import DEFAULT_RASPIOS_IMAGE
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
    shutil.copyfile('scripts/cmdline.txt', os.path.join(mountpoint, 'cmdline.txt'))
    shutil.copyfile('scripts/dhcpcd.conf', os.path.join(mountpoint, 'dhcpcd.conf'))
    # TODO: integrate this apps in the image
    shutil.copyfile('scripts/apt-offline-1.8.5.tar.gz', os.path.join(mountpoint, 'apt-offline-1.8.5.tar.gz'))
    shutil.copyfile('scripts/apt-update-20230207.zip', os.path.join(mountpoint, 'apt-update-20230207.zip'))
    shutil.copyfile('scripts/x2goserver-apt.zip', os.path.join(mountpoint, 'x2goserver-apt.zip'))


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


def insert_ssh_include():
    config_dir = os.path.join(os.path.expanduser('~'), '.ssh/')
    master_config_path = os.path.join(config_dir, 'config')
    tower_config_path = os.path.join(config_dir, 'tower')
    directive = f"Include {tower_config_path}"

    if os.path.exists(master_config_path):
        with open(master_config_path, 'r') as f:
            current_config = f.read()
        if directive not in current_config:
            with open(master_config_path, 'a') as f:
                f.write("\n")
                f.write(directive)
    else:
        with open(master_config_path, 'w') as f:
            f.write(directive)


def update_ssh_config(name, ip):
    insert_ssh_include()
    config_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'tower')
    key_path = os.path.join(os.path.expanduser('~'), '.ssh/', name)
    config = read_ssh_config(config_path) if os.path.exists(config_path) else empty_ssh_config_file()
    existing_hosts = config.hosts()

    if name in existing_hosts:
        config.set(name, Hostname=ip)
        config.save()
        return

    for host_name in existing_hosts:
        host = config.host(host_name)
        if host['hostname'] == ip:
            config.rename(host_name, name)
            config.set(name, IdentityFile=key_path)
            config.save()
            return
    
    config.add(name,
        Hostname=ip,
        User="tower",
        IdentityFile=key_path,
        StrictHostKeyChecking="no",
        LogLevel="FATAL"
    )
    config.write(config_path)
    print(f"{config_path} updated")


# 1. Download image
# 2. Prepare firstrun.sh
# 3. Burn image
# 4. Copy files in sd-card
# 5. Discover IP
# 6. Update ssh config file
# 6. Update computer config
def burn_image(dir, config):
    download_latest_image(config["default-raspios-image"])
    firstrun_script = generate_firstrun_script(config)
    osutils.write_image(".cache/raspios.img", config['sd-card'])
    copy_firstrun_files(config['sd-card'], firstrun_script)
    # TODO: unmount device
    print(f"SD Card ready. Please unmount and insert the SD-Card in the Raspberry-PI, turn it on and wait for it to be detected on the network.")
    ip = discover_ip(config['name'])
    update_ssh_config(config['name'], ip)
    # TODO: let's think if we can get rid of computers.ini
    computers.set_computer_config(dir, config['name'], 'ip', ip)
