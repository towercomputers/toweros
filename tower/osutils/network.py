import binascii
import configparser
from io import StringIO
import os
import fcntl
import struct
import socket
import ipaddress

from backports.pbkdf2 import pbkdf2_hmac
import sh
from sh import iw, iwconfig


def derive_wlan_key(ssid, psk):
    return binascii.hexlify(pbkdf2_hmac("sha1", psk.encode("utf-8"), ssid.encode("utf-8"), 4096, 32)).decode()

def get_connected_ssid():
    try:
        buf = StringIO()
        iwconfig(_out=buf)
        result = buf.getvalue()
        ssid = result.split('ESSID:"')[1].split('"')[0]
        return ssid
    except: # no need to be curious here
        return None

def get_ssid_password(ssid):
    try:
        network_manager_conf_path = f'/etc/NetworkManager/system-connections/{ssid}.nmconnection'
        if os.path.exists(network_manager_conf_path):
            wlan_conf = configparser.ConfigParser()
            wlan_conf.read(network_manager_conf_path)
            password = wlan_conf['wifi-security']['psk']
            return password
        wpa_supplicant_path = '/etc/wpa_supplicant/wpa_supplicant.conf'
        if os.path.exists(wpa_supplicant_path):
            with open(wpa_supplicant_path) as f:
                wlan_conf = f.read()
            password = wlan_conf.split('psk=')[1].split('\n')[0].strip().replace('"', '')
            return password
        return None
    except: # no need to be curious here
        return None

def scan_wifi_countries():
    buf = StringIO()
    with sh.contrib.sudo(password="", _with=True):
        iw('dev', 'wlan0', 'scan', _out=buf)
    result = buf.getvalue()
    bss = result.split('BSS ')
    wifis= {}
    for info in bss:
        if info.find("SSID: ") != -1:
            ssid = info.split('SSID: ')[1].split('\t')[0].strip()
            cc = '--'
            if info.find("Country: ") != -1:
                cc = info.split("Country: ")[1].split('\t')[0]
            if ssid not in wifis or wifis[ssid] == '--':
                wifis[ssid] = cc
    return wifis

def find_wlan_country(ssid):
    wifi_countries = scan_wifi_countries()
    if ssid in wifi_countries and wifi_countries[ssid] != '--':
        return wifi_countries[ssid]
    count_by_country = {}
    max_cc = ''
    max_count = 0
    for wid in wifi_countries:
        cc = wifi_countries[wid]
        if cc != '--':
            if cc not in count_by_country:
                count_by_country[cc] = 1
            else:
                count_by_country[cc] += 1
            if count_by_country[cc] > max_count:
                max_count = count_by_country[cc]
                max_cc = cc
    return max_cc

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
    netmask = get_interface_netmask(ifname)
    return str(ipaddress.ip_network(f'{ip}/{netmask}', strict=False))