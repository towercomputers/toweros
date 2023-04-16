import os
import secrets
import sys
import time
import logging
from urllib.parse import urlparse
import hashlib
import glob

import requests
from passlib.hash import sha512_crypt
import sh
from sh import ssh, scp, ssh_keygen, xz, cat, mount, parted
from sh import Command, ErrorReturnCode_1, ErrorReturnCode

from tower import utils
from tower import towerospi
from tower import sshconf

logger = logging.getLogger('tower')

class MissingEnvironmentValue(Exception):
    pass

class UnkownHost(Exception):
    pass

def check_environment_value(key, value):
    if not value:
        raise MissingEnvironmentValue(f"Impossible to determine the {key}. Please use the option --{key}.")

def generate_key_pair(name):
    ssh_dir = os.path.join(os.path.expanduser('~'), '.ssh/')
    key_path = os.path.join(ssh_dir, f'{name}')
    if os.path.exists(key_path):
        os.remove(key_path)
        os.remove(f'{key_path}.pub')
    ssh_keygen('-t', 'ed25519', '-C', name, '-f', key_path, '-N', "")
    return f'{key_path}.pub', key_path

def prepare_wifi_parameters(args):
    online, wlan_ssid, wlan_password = 'false', '', ''
    if args.online:
        online = 'true'
        wlan_ssid = args.wlan_ssid or utils.get_connected_ssid()
        check_environment_value('wlan-ssid', wlan_ssid)
        if args.wlan_password:
            wlan_password = utils.derive_wlan_key(wlan_ssid, args.wlan_password)
        else:
            wlan_password = utils.get_ssid_presharedkey(wlan_ssid)
        check_environment_value('wlan-password', wlan_password)
    return online, wlan_ssid, wlan_password

def get_network_infos(args):
    interface = args.ifname if args.ifname else utils.find_wired_interface()
    check_environment_value('ifname', interface)
    thin_client_ip = utils.get_interface_ip(interface)
    tower_network = utils.get_interface_network(interface)
    if not thin_client_ip or not tower_network:
        raise MissingEnvironmentValue(f"Impossible to determine the thin client IP/Network. Please ensure you are connected to the network on `{interface}`.")
    return thin_client_ip, tower_network

@utils.clitask("Preparing host configuration...")
def prepare_host_config(args):
    name = args.name[0]
    # public key for ssh
    check_environment_value('public-key-path', args.public_key_path)
    with open(args.public_key_path) as f:
        public_key = f.read().strip()
    # generate random password
    password = secrets.token_urlsafe(16)
    # gather locale informations
    keymap = args.keymap or utils.get_keymap()
    timezone = args.timezone or utils.get_timezone()
    lang = args.lang or utils.get_lang()
    # determine wifi parameters
    online, wlan_ssid, wlan_password = prepare_wifi_parameters(args)
    # determine thinclient IP and network
    thin_client_ip, tower_network = get_network_infos(args)
    # return complete configuration
    return {
        'HOSTNAME': name,
        'USERNAME': sshconf.DEFAULT_SSH_USER,
        'PUBLIC_KEY': public_key,
        'PASSWORD_HASH': sha512_crypt.hash(password),
        'KEYMAP': keymap,
        'TIMEZONE': timezone,
        'LANG': lang,
        'ONLINE': online,
        'WLAN_SSID': wlan_ssid,
        'WLAN_SHARED_KEY': wlan_password,
        'THIN_CLIENT_IP': thin_client_ip,
        'TOWER_NETWORK': tower_network,
    }

@utils.clitask("Decompressing {0}...")
def decompress_image(image_path):
    out_file = image_path.replace('.xz', '')
    xz('--stdout', '-d', image_path, _out=out_file)
    return out_file

def prepare_host_image(image_arg):
    image_path = image_arg if image_arg and os.path.isfile(image_arg) else utils.find_host_image()
    if image_path:
        ext = image_path.split(".").pop()
        if ext == 'xz': # TODO: support more formats
            image_path = decompress_image(image_path)
    return image_path

def prepare_provision(args):
    # generate key pair
    if not args.public_key_path:
        args.public_key_path, private_key_path = generate_key_pair(args.name[0])
    # generate host configuration
    host_config = prepare_host_config(args)
    # determine target device
    sd_card = args.sd_card or utils.select_sdcard_device()
    check_environment_value('sd-card', sd_card)
    # find TowerOS PI image
    image_path = prepare_host_image(args.image)
    check_environment_value('image', image_path)
    # return everything needed to provision the host
    return image_path, sd_card, host_config, private_key_path

@utils.clitask("Provisioning `{0}`...", timer_message="Host provisioned in {}s")
def provision(name, image_path, sd_card, host_config, private_key_path):
    towerospi.burn_image(image_path, sd_card, host_config)
    logger.info(f"SD Card ready. Please insert the SD Card into the Host computer, then turn it on and wait for it to be detected on the network.")
    sshconf.discover_and_update(name, private_key_path, host_config['TOWER_NETWORK'])
    print(f"Access the host `web` with the command `$ ssh web`.")
    print(f"Install a package on `web` with the command `$ tower install web <package-name>`")
    print(f"Run a GUI application on `web` with the command `$ tower run web <package-name>`")
