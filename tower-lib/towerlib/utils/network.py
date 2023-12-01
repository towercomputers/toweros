import binascii
import socket
import logging

import requests
from backports.pbkdf2 import pbkdf2_hmac
from sh import cp, Command

from towerlib.utils.decorators import clitask
from towerlib.utils.shell import sh_sudo

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
    tmp_dest_path = "/tmp/" + dest_path.split("/")[-1]
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(tmp_dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=4096):
                f.write(chunk)
    with sh_sudo(password="", _with=True):
        cp(tmp_dest_path, dest_path)

def interface_is_up(interface):
    is_up = Command('sh')('-c', f'ip link show {interface} | grep -q "state UP" && echo "OK" || echo "NOK"').strip()
    return is_up == "OK"

def is_ip_attached(interface, ip):
    is_attached = Command('sh')('-c', f'ip addr show {interface} | grep -q {ip} && echo "OK" || echo "NOK"').strip()
    return is_attached == "OK"
