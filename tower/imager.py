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


# TODO: all this files should be already in the image
def copy_firstrun_files(device):
    for filename in os.listdir('firstrun/'):
        shutil.copyfile(f'firstrun/{filename}', os.path.join(mountpoint, filename))


def set_firstrun_env(device, firstrun_env):
    env = "\n".join([f'{key}="{value}"' for key, value in firstrun_env.items()])
    with open(os.path.join(mountpoint, 'tower.env'), "w") as f:
        f.write(env)


def burn_image(image_url, device, firstrun_env):
    image_path = download_latest_image(image_url)
    osutils.write_image(image_path, device)
    set_firstrun_env(device, firstrun_env)
    copy_firstrun_files(device)
    # TODO: unmount device

