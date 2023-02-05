import binascii
import configparser
import os
import ipaddress
from random import randint
from argparse import ArgumentParser
import re
import secrets
from sh import ssh_keygen

from passlib.hash import sha512_crypt
from backports.pbkdf2 import pbkdf2_hmac

from tower import osutils

DEFAULT_RASPIOS_IMAGE = "https://downloads.raspberrypi.org/raspios_arm64/images/raspios_arm64-2022-09-26/2022-09-22-raspios-bullseye-arm64.img.xz"
DEFAULT_SSH_USER = "tower"
DEFAULT_SSH_PORT = 22

class MissingConfigValue(Exception):
    pass

def default_config_dir():
    home_path = os.path.expanduser('~')
    return os.path.join(home_path, '.config/', 'tower/')

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

def write_config_file(config, dir, filename):
    config_dir = dir or default_config_dir()
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    config_file = os.path.join(config_dir, f'{filename}')
    with open(config_file, 'w') as f:
        config.write(f)

def check_missing_value(key, value):
    if not value:
        raise MissingConfigValue(f"Impossible to determine the {key}. Please use the option --{key}.")

def derive_wlan_key(ssid, psk):
    return binascii.hexlify(pbkdf2_hmac("sha1", psk.encode("utf-8"), ssid.encode("utf-8"), 4096, 32)).decode()

def create_computer_config(args):
    name = args.name[0]

    public_key_path, private_key_path = args.public_key_path, args.private_key_path
    if not public_key_path:
        public_key_path, private_key_path = generate_key_pair(name)
    
    with open(public_key_path) as f:
        public_key = f.read().strip()

    password = secrets.token_urlsafe(16)

    sd_card = args.sd_card or osutils.select_sdcard_device()
    check_missing_value('sd-card', sd_card)
    
    keymap = args.keymap or osutils.get_keymap()
    timezone = args.timezone or osutils.get_timezone()

    if args.online:
        online = 'true'
        wlan_ssid = args.wlan_ssid or osutils.get_connected_ssid()
        check_missing_value('wlan-ssid', wlan_ssid)
        wlan_password = args.wlan_password or osutils.get_ssid_password(wlan_ssid)
        check_missing_value('wlan-password', wlan_password)
        wlan_password = derive_wlan_key(wlan_ssid, wlan_password)
        wlan_country = args.wlan_country or osutils.find_wlan_country(wlan_ssid)
        check_missing_value('wlan-country', wlan_country)
    else:
        online = 'false'
        wlan_ssid, wlan_password, wlan_country = '', '', ''

    config = configparser.ConfigParser()
    config[configparser.DEFAULTSECT] = {
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
    write_config_file(config, args.config_dir, f'{name}.ini')
    
    return config[configparser.DEFAULTSECT]

def create_application_config(args):
    config = configparser.ConfigParser()
    config[configparser.DEFAULTSECT] = {
        'name': args.name,
        'alias': args.alias,
        'path': args.path,
        'apt-packages': args.apt_packages or "",
        'local-apt-packages': args.local_apt_packages or "",
    }
    write_config_file(config, args.config_dir, f'{args.name}.{args.alias}.ini')

    return config[configparser.DEFAULTSECT]

def get_tower_config(dir):
    config = configparser.ConfigParser()
    section = configparser.DEFAULTSECT

    config_dir = dir or default_config_dir()
    config_file = os.path.join(config_dir, 'tower_config.conf') # TODO: put computer and apps files in subfolders or just one file for everything
    if os.path.exists(config_file):
        config.read(config_file)
        section = config.sections()[0]

    config[section]['default-ssh-user'] = config[section].get('default-ssh-user', DEFAULT_SSH_USER)
    config[section]['default-ssh-port'] = config[section].get('default-ssh-port', f'{DEFAULT_SSH_PORT}')
    config[section]['default-raspios-image'] = config[section].get('default-raspios-image', f'{DEFAULT_RASPIOS_IMAGE}')
    
    return config[section]

def get_computer_config(dir, name):
    config_dir = dir or default_config_dir()
    config_file = os.path.join(config_dir, f'{name}.ini')
    config = configparser.ConfigParser()
    config.read(config_file)
    return config[configparser.DEFAULTSECT]

def get_application_config(dir, name, alias):
    config_dir = dir or default_config_dir()
    config_file = os.path.join(config_dir, f'{name}.{alias}.ini')
    config = configparser.ConfigParser()
    config.read(config_file)
    return config[configparser.DEFAULTSECT]