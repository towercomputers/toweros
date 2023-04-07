import os
import secrets
from io import StringIO
import sys
import time
import logging
from urllib.parse import urlparse
import hashlib
import glob

import requests
from passlib.hash import sha512_crypt
import sh
from sh import ssh, scp, ssh_keygen, xz, avahi_resolve, cat, mount, parted
from sh import Command, ErrorReturnCode_1, ErrorReturnCode
from sshconf import read_ssh_config, empty_ssh_config_file

from tower import utils
from tower import towerospi

DEFAULT_SSH_USER = "tower"

logger = logging.getLogger('tower')

class MissingEnvironmentValue(Exception):
    pass

class UnkownHost(Exception):
    pass


def check_environment_value(key, value):
    if not value:
        raise MissingEnvironmentValue(f"Impossible to determine the {key}. Please use the option --{key}.")


def is_valid_https_url(str):
    try:
        result = urlparse(str)
        return all([result.scheme, result.netloc]) and result.scheme == 'https'
    except:
        return False


def generate_key_pair(name):
    ssh_dir = os.path.join(os.path.expanduser('~'), '.ssh/')
    key_path = os.path.join(ssh_dir, f'{name}')
    if os.path.exists(key_path):
        os.remove(key_path)
        os.remove(f'{key_path}.pub')
    ssh_keygen('-t', 'ed25519', '-C', name, '-f', key_path, '-N', "")
    return f'{key_path}.pub', key_path


def prepare_host_config(args):
    logger.info("Preparing host configuration...")
    name = args.name[0]
    
    check_environment_value('public-key-path', args.public_key_path)
    with open(args.public_key_path) as f:
        public_key = f.read().strip()

    password = secrets.token_urlsafe(16)
    
    keymap = args.keymap or utils.get_keymap()
    timezone = args.timezone or utils.get_timezone()
    lang = args.lang or utils.get_lang()

    if args.online:
        online = 'true'
        wlan_ssid = args.wlan_ssid or utils.get_connected_ssid()
        check_environment_value('wlan-ssid', wlan_ssid)
        if args.wlan_password:
            wlan_password = utils.derive_wlan_key(wlan_ssid, args.wlan_password)
        else:
            wlan_password = utils.get_ssid_presharedkey(wlan_ssid)
        check_environment_value('wlan-password', wlan_password)
    else:
        online = 'false'
        wlan_ssid, wlan_password = '', '', ''
    
    wired_interfaces = utils.get_wired_interfaces()
    if not wired_interfaces:
        raise MissingEnvironmentValue(f"Impossible to determine the thin client IP/Network. Please ensure you are connected to a wired network.")
    
    interface = wired_interfaces[0]  # TODO: make the interface configurable ?
    thin_client_ip = utils.get_interface_ip(interface)
    tower_network = utils.get_interface_network(interface)
    if not thin_client_ip or not tower_network:
        raise MissingEnvironmentValue(f"Impossible to determine the thin client IP/Network. Please ensure you are connected to the network on `{interface}`.")
  
    return {
        'HOSTNAME': name,
        'USERNAME': DEFAULT_SSH_USER,
        'PUBLIC_KEY': public_key,
        'ENCRYPTED_PASSWORD': sha512_crypt.hash(password),
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
    xz('-d', image_path)
    return image_path.replace('.xz', '')


def find_host_image(image_arg):
    image_path = None
    if image_arg and os.path.isfile(image_arg):
        image_path = image_arg
    else:
        builds_dirs = [
            os.path.join(os.getcwd(), 'builds'),
            os.path.join(os.path.expanduser('~'), '.cache', 'tower', 'builds')
        ]
        for builds_dir in builds_dirs:
            if os.path.isdir(builds_dir):
                host_images = glob.glob(os.path.join(builds_dir, 'towerospi-*.xz'))
                host_images += glob.glob(os.path.join(builds_dir, 'towerospi-*.img'))
                if host_images:
                    image_path = host_images.pop()
                    break
    if image_path:
        ext = image_path.split(".").pop()
        if ext == 'xz': # TODO: support more formats
            image_path = decompress_image(image_path)
    return image_path


def prepare_provision(args):
    if not args.public_key_path:
        args.public_key_path, private_key_path = generate_key_pair(args.name[0])

    host_config = prepare_host_config(args)
    
    sd_card = args.sd_card or utils.select_sdcard_device()
    check_environment_value('sd-card', sd_card)

    image_path = find_host_image(args.image)
    check_environment_value('image', image_path)

    return image_path, sd_card, host_config, private_key_path


def insert_include_directive():
    config_dir = os.path.join(os.path.expanduser('~'), '.ssh/')
    master_config_path = os.path.join(config_dir, 'config')
    tower_config_path = os.path.join(config_dir, 'tower.conf')
    directive = f"Include {tower_config_path}"
    if os.path.exists(master_config_path):
        with open(master_config_path, 'r') as f:
            current_config = f.read()
        if directive not in current_config:
            with open(master_config_path, 'r+') as f:
                content = f.read()
                f.seek(0, 0)
                f.write(directive + '\n\n' + content)
    else:
        with open(master_config_path, 'w') as f:
            f.write(directive)


def ssh_config():
    config_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'tower.conf')
    config = read_ssh_config(config_path) if os.path.exists(config_path) else empty_ssh_config_file()
    return config


def get_config(name):
    config = ssh_config()
    if name in config.hosts():
        return config.host(name)
    else:
        return None


def update_config(name, ip, private_key_path):
    insert_include_directive()

    config_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'tower.conf')
    config = read_ssh_config(config_path) if os.path.exists(config_path) else empty_ssh_config_file()
    existing_hosts = config.hosts()

    if name in existing_hosts:
        config.set(name, Hostname=ip)
        config.save()
        return

    for host_name in existing_hosts:
        host = config.host(host_name)
        if host['hostname'] == ip:
            config.rename(host_name, name)
            config.set(name, IdentityFile=private_key_path)
            config.save()
            return
    
    config.add(name,
        Hostname=ip,
        User=DEFAULT_SSH_USER,
        IdentityFile=private_key_path,
        # TODO: clean known_hosts
        #StrictHostKeyChecking="no",
        LogLevel="FATAL"
    )
    config.write(config_path)
    logger.info(f"{config_path} updated")


def get_list():
    return ssh_config().hosts()


def exists(name):
    return name in get_list()


def is_online(name):
    if exists(name):
        result = ssh(name, 'sudo', 'ifconfig')
        return "wlan0" in result
    raise UnkownHost(f"Unknown host: {name}")


def discover_ip(host_name):
    result = avahi_resolve('-4', '-n', f'{host_name}.local')
    if result != "":
        ip = result.strip().split("\t").pop()
        logger.info(f"IP found: {ip}")
        return ip
    logger.info(f"Fail to discover the IP for {host_name}. Retrying in 10 seconds with avahi")
    time.sleep(10)
    return discover_ip(host_name)


def copy_file(host_name_src, host_name_dest, filename):
    scp('-3', f'{host_name_src}:{filename}', f'{host_name_dest}:{filename}', _out=logger.debug)


def clean_install_files(host_name, packages, online_host=None):
    proxy = host_name if online_host is None else online_host
    install_name = "_".join(packages)
    sig_filename = os.path.join('~/Downloads', f'{install_name}-apt.sig')
    bundle_filename = os.path.join('~/Downloads', f'{install_name}-apt-bundle.zip')
    try:
        ssh(proxy, 'rm', '-f', sig_filename, _out=logger.debug)
        ssh(host_name, 'rm', '-f', bundle_filename, _out=logger.debug)
        if proxy != host_name:
            ssh(host_name, 'rm', '-f', sig_filename, _out=logger.debug)
            ssh(proxy, 'rm', '-f', bundle_filename, _out=logger.debug)
    except ErrorReturnCode_1 as e:
       pass


def run_application(host, port, username, key_filename, command):
    cli = x2go.X2GoClient(use_cache=False, loglevel=x2go.log.loglevel_DEBUG)
    s_uuid = cli.register_session(
        host, 
        port=port,
        username=username,
        cmd=command,
        look_for_keys=False,
        key_filename=key_filename
    )
    cli.connect_session(s_uuid)
    cli.clean_sessions(s_uuid)
    cli.start_session(s_uuid)

    try:
        while cli.session_ok(s_uuid):
            gevent.sleep(2)
    except KeyboardInterrupt:
        pass

    cli.suspend_session(s_uuid)


def provision(name, image_path, sd_card, host_config, private_key_path):
    towerospi.burn_image(image_path, sd_card, host_config)
    print(f"SD Card ready. Please insert the SD-Card in the Raspberry-PI, turn it on and wait for it to be detected on the network.")
    ip = discover_ip(name)
    update_config(name, ip, private_key_path)


def install(host_name, packages, online_host=None):
    proxy = host_name if online_host is None else online_host
    install_name = "_".join(packages)
    try:
        logger.info("Generate package signature in target host.")
        sig_filename = os.path.join('~/', f'{install_name}-apt.sig')
        ssh(host_name, 'sudo', 'apt-offline',
            'set', sig_filename, '--install-packages', *packages, _out=logger.debug)

        logger.info("Copy package signature to online host.")
        if proxy != host_name:
            copy_file(host_name, proxy, sig_filename)

        logger.info("Downloading bundle...")
        bundle_filename = os.path.join('~/', f'{install_name}-apt-bundle.zip')
        ssh(proxy, 'sudo', 'apt-offline',
            'get', sig_filename, '--bundle', bundle_filename, _out=logger.debug)

        logger.info("Copy bundle to target host.")
        if proxy != host_name:
            copy_file(proxy, host_name, bundle_filename)

        logger.info("Install bundle in target host.")
        ssh(host_name, 'sudo', 'apt-offline', 'install', bundle_filename, _out=logger.debug)
        ssh(host_name, 'sudo', 'apt-get', '--assume-yes', 'install', *packages, _out=logger.debug)
        clean_install_files(host_name, packages, online_host)
    except ErrorReturnCode as e:
        clean_install_files(host_name, packages, online_host)
        raise(e)

def status(host_name = None):
    if host_name:
        host_config = get_config(host_name)
        host_status = 'up'
        try:
            ssh(host_name, 'ls') # any ssh command sould make the job
        except ErrorReturnCode:
            host_status = 'down'
        online = is_online(host_name) if host_status == 'up' else "N/A"
        return {
            'name': host_name,
            'status': host_status,
            'online-host': online,
            'ip': host_config['hostname']
        }
    return [status(host_name) for host_name in get_list()]
