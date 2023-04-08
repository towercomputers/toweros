import binascii
import configparser
from io import StringIO
import os
import fcntl
import struct
import socket
import ipaddress
import array
import logging

import requests
import sh
from sh import cat
from backports.pbkdf2 import pbkdf2_hmac

from tower.utils.decorators import clitask

logger = logging.getLogger('tower')

def derive_wlan_key(ssid, psk):
    return binascii.hexlify(pbkdf2_hmac("sha1", psk.encode("utf-8"), ssid.encode("utf-8"), 4096, 32)).decode()
    
def get_connected_ssid():
    try:
        ifnames = get_wireless_interfaces()
        if not ifnames:
            return None
        ifname = ifnames[0] # assume one wifi connection
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        essidBuf = array.array("b", [0] * 32) # 32: essid max length
        essidPointer, essidLength = essidBuf.buffer_info()
        # 16: ifname max legth
        request = struct.pack('16sPHH', bytes(ifname, 'utf8'), essidPointer, essidLength, 0)
        fcntl_res = fcntl.ioctl(
            s.fileno(),
            0x8B1B, # SIOCGIWESSID
            request
        )
        ssid = "".join([chr(c) for c in essidBuf if c != 0])
        if not ssid:
            return None
        return ssid
    except OSError as e:
        if e.errno == 19: # No such device
            return None

def get_ssid_presharedkey(ssid):
    try:
        iwdspot_path = f'/var/lib/iwd/{ssid}.psk'
        try:
            with sh.contrib.sudo(password="", _with=True):
                iwdspot_conf = cat(iwdspot_path)
                return iwdspot_conf.split("PreSharedKey=")[1].split("\n")[0].strip()
        except sh.sh.ErrorReturnCode:
            pass
        return None
    except: # no need to be curious here
        return None

def get_interface_info(ifname, ioctl_command):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                ioctl_command,
                struct.pack('256s', bytes(ifname[:15], 'utf-8'))
            )[20:24])
    except OSError as e:
        if e.errno == 19: # No such device
            return None

def get_interface_ip(ifname):
    return get_interface_info(ifname, 0x8915) # SIOCGIFADDR

def get_interface_netmask(ifname):
    return get_interface_info(ifname,  0x891B) # SIOCGIFNETMASK

def get_interface_network(ifname):
    ip = get_interface_ip(ifname)
    if not ip:
        return None
    netmask = get_interface_netmask(ifname)
    return str(ipaddress.ip_network(f'{ip}/{netmask}', strict=False))

def get_wired_interfaces():
    return [i[1] for i in socket.if_nameindex() if i[1].startswith('e')]

def get_wireless_interfaces():
    return [i[1] for i in socket.if_nameindex() if i[1].startswith('w')]

@clitask("Downloading {0} in {1}...")
def download_file(url, dest_path):
    with requests.get(url, stream=True) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=4096):
                f.write(chunk)