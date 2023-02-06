import binascii
import configparser
import os
import ipaddress
from random import randint
from argparse import ArgumentParser
import re
import secrets

from passlib.hash import sha512_crypt

from tower import osutils
from tower import configs


def create_computer_config(args):
    name = args.name[0]

    public_key_path, private_key_path = args.public_key_path, args.private_key_path
    if not public_key_path:
        public_key_path, private_key_path = osutils.generate_key_pair(name)
    
    with open(public_key_path) as f:
        public_key = f.read().strip()

    password = secrets.token_urlsafe(16)

    sd_card = args.sd_card or osutils.select_sdcard_device()
    configs.check_missing_value('sd-card', sd_card)
    
    keymap = args.keymap or osutils.get_keymap()
    timezone = args.timezone or osutils.get_timezone()

    if args.online:
        online = 'true'
        wlan_ssid = args.wlan_ssid or osutils.get_connected_ssid()
        configs.check_missing_value('wlan-ssid', wlan_ssid)
        wlan_password = args.wlan_password or osutils.get_ssid_password(wlan_ssid)
        configs.check_missing_value('wlan-password', wlan_password)
        wlan_password = osutils.derive_wlan_key(wlan_ssid, wlan_password)
        wlan_country = args.wlan_country or osutils.find_wlan_country(wlan_ssid)
        configs.check_missing_value('wlan-country', wlan_country)
    else:
        online = 'false'
        wlan_ssid, wlan_password, wlan_country = '', '', ''
  
    config = configs.read_config(args.config_dir, 'computers.ini')
    config[name] = {
        'name': name,
        'sd-card': sd_card,
        'public-key': public_key,
        'private-key-path': private_key_path,
        'password': password,
        'encrypted-password': sha512_crypt.hash(password),
        'keymap': keymap,
        'timezone': timezone,
        'online': online,
        'wlan-ssid': wlan_ssid,
        'wlan-password': wlan_password,
        'wlan-country': wlan_country,
    }
    configs.write_config(args.config_dir, 'computers.ini', config)
    
    return config[name]

def get_computer_config(dir, name):
    config = configs.read_config(dir, 'computers.ini')
    if name in config:
        return config[name]
    else:
        return None

def get_computer_list(dir):
    config = configs.read_config(dir, 'computers.ini')
    return config.sections()

def computer_exists(dir, name):
    return True if get_computer_config(dir, name) is not None else False
