import binascii
import socket
import logging

import requests
from backports.pbkdf2 import pbkdf2_hmac

from tower.utils.decorators import clitask

logger = logging.getLogger('tower')

def derive_wlan_key(ssid, psk):
    return binascii.hexlify(pbkdf2_hmac("sha1", psk.encode("utf-8"), ssid.encode("utf-8"), 4096, 32)).decode()

def get_wired_interfaces():
    return [i[1] for i in socket.if_nameindex() if i[1].startswith('e')]

def get_wireless_interfaces():
    return [i[1] for i in socket.if_nameindex() if i[1].startswith('w')]

def get_interfaces():
    return get_wired_interfaces() + get_wireless_interfaces()

@clitask("Downloading {0}...")
def download_file(url, dest_path):
    with requests.get(url, stream=True) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=4096):
                f.write(chunk)
