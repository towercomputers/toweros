import binascii
import time
import os

from sh import Command
from backports.pbkdf2 import pbkdf2_hmac

from tower import osutils

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

def discover_wlan_params():
    ssid, psk = osutils.get_wlan_infos()
    return dict(
        WLAN_SSID = ssid,
        WLAN_PASSWORD = derive_wlan_key(ssid, psk),
        WLAN_COUNTRY = find_wlan_country(ssid),
    )

def write_image(image, device):
    start_time = time.time()
    if os.path.exists(osutils.rpi_imager_path()):
        osutils.disable_rpi_image_ejection()
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