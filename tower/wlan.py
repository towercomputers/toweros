import binascii

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