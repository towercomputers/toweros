import binascii
import time
import os

from backports.pbkdf2 import pbkdf2_hmac
import sh
from sh import Command, ssh_keygen

from tower import osutils

def default_ssh_dir():
    home_path = os.path.expanduser('~')
    return os.path.join(home_path, '.ssh/')

def generate_key_pair(name):
    ssh_dir = default_ssh_dir()
    key_path = os.path.join(ssh_dir, f'{name}')
    if os.path.exists(key_path):
        os.remove(key_path)
        os.remove(f'{key_path}.pub')
    ssh_keygen('-t', 'ed25519', '-C', name, '-f', key_path, '-N', "")
    return f'{key_path}.pub', key_path

def derive_wlan_key(ssid, psk):
    return binascii.hexlify(pbkdf2_hmac("sha1", psk.encode("utf-8"), ssid.encode("utf-8"), 4096, 32)).decode()

def find_wlan_country(ssid):
    wifi_countries = osutils.scan_wifi_countries()
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

def write_image(image, device):
    start_time = time.time()
    if os.path.exists(osutils.rpi_imager_path()):
        osutils.disable_rpi_image_ejection()
        rpi_imager = Command(osutils.rpi_imager_path())
        print(f"Burning {device} with rpi-imager, be patient please...")
        with sh.contrib.sudo:
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

def select_sdcard_device():
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
        print("sd-card not found.")
        return None
    elif (len(new_devices) > 1):
        print("More than one disk found.")
        return None
    else:
        print(f"sd-card found: {new_devices[0]}")
        return new_devices[0]