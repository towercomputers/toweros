import binascii
import configparser
from io import StringIO
import os
import fcntl
import struct
import socket
import ipaddress
import array

from backports.pbkdf2 import pbkdf2_hmac
import sh
from sh import iw, cat


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
        iwdspot_path = f'/var/lib/iwd/{ssid}.psk'
        try:
            buf = StringIO()
            with sh.contrib.sudo(password="", _with=True):
                cat(iwdspot_path, _out=buf)
                iwdspot_conf = buf.getvalue()
                password = iwdspot_conf.split("Passphrase=")[1].split("\n")[0].strip()
                return derive_wlan_key(ssid, password)
        except sh.sh.ErrorReturnCode:
            pass
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
    if not ip:
        return None
    netmask = get_interface_netmask(ifname)
    return str(ipaddress.ip_network(f'{ip}/{netmask}', strict=False))

def get_wired_interfaces():
    return [i[1] for i in socket.if_nameindex() if i[1].startswith('e')]

def get_wireless_interfaces():
    return [i[1] for i in socket.if_nameindex() if i[1].startswith('w')]
