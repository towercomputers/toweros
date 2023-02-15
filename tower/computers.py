import os
import secrets
from io import StringIO
import sys
import time
import logging

from passlib.hash import sha512_crypt
from sh import ssh, scp, arp, ssh_keygen, ErrorReturnCode_1, ErrorReturnCode
from sshconf import read_ssh_config, empty_ssh_config_file

from tower import osutils
from tower import defaults

logger = logging.getLogger('tower')

class MissingEnvironmentValue(Exception):
    pass

class UnkownComputer(Exception):
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


def firstrun_env(args):
    logger.info("Generating first run environment...")
    name = args.name[0]
    
    check_environment_value('public-key-path', args.public_key_path)
    with open(args.public_key_path) as f:
        public_key = f.read().strip()

    password = secrets.token_urlsafe(16)
    
    keymap = args.keymap or osutils.get_keymap()
    timezone = args.timezone or osutils.get_timezone()

    if args.online:
        online = 'true'
        wlan_ssid = args.wlan_ssid or osutils.get_connected_ssid()
        check_environment_value('wlan-ssid', wlan_ssid)
        wlan_password = args.wlan_password or osutils.get_ssid_password(wlan_ssid)
        check_environment_value('wlan-password', wlan_password)
        wlan_country = args.wlan_country or osutils.find_wlan_country(wlan_ssid)
        check_environment_value('wlan-country', wlan_country)
    else:
        online = 'false'
        wlan_ssid, wlan_password, wlan_country = '', '', ''
  
    return {
        'NAME': name,
        'PUBLIC_KEY': public_key,
        'ENCRYPTED_PASSWORD': sha512_crypt.hash(password),
        'KEYMAP': keymap,
        'TIMEZONE': timezone,
        'ONLINE': online,
        'WLAN_SSID': wlan_ssid,
        'WLAN_PASSWORD': wlan_password,
        'WLAN_COUNTRY': wlan_country,
        'USER': defaults.DEFAULT_SSH_USER
    }


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
        User=defaults.DEFAULT_SSH_USER,
        IdentityFile=private_key_path,
        StrictHostKeyChecking="no",
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
        buf = StringIO()
        ssh(name, 'sudo', 'ifconfig', _out=buf)
        result = buf.getvalue()
        return "wlan0" in result
    raise UnkownComputer(f"Unknown computer: {name}")


def discover_ip(computer_name):
    buf = StringIO()
    arp('-a', _out=buf)
    result = buf.getvalue()
    lines = result.split("\n")
    for line in lines:
        if line.startswith(f'{computer_name}.local'):
            ip = line.split("(")[1].split(")")[0]
            logger.info(f"IP found: {ip}")
            return ip
    logger.info(f"Fail to discover the IP for {computer_name}. Retrying in 10 seconds")
    time.sleep(10)
    return discover_ip(computer_name)


def copy_file(computer_name_src, computer_name_dest, filename):
    scp('-3', f'{computer_name_src}:{filename}', f'{computer_name_dest}:{filename}', _out=logger.debug)


def clean_install_files(computer_name, packages, online_computer=None):
    proxy = computer_name if online_computer is None else online_computer
    install_name = "_".join(packages)
    sig_filename = os.path.join('~/Downloads', f'{install_name}-apt.sig')
    bundle_filename = os.path.join('~/Downloads', f'{install_name}-apt-bundle.zip')
    try:
        ssh(proxy, 'rm', '-f', sig_filename, _out=logger.debug)
        ssh(computer_name, 'rm', '-f', bundle_filename, _out=logger.debug)
        if proxy != computer_name:
            ssh(computer_name, 'rm', '-f', sig_filename, _out=logger.debug)
            ssh(proxy, 'rm', '-f', bundle_filename, _out=logger.debug)
    except ErrorReturnCode_1 as e:
       pass


def install(computer_name, packages, online_computer=None):
    proxy = computer_name if online_computer is None else online_computer
    install_name = "_".join(packages)
    try:
        logger.info("Generate package signature in target computer.")
        sig_filename = os.path.join('~/Downloads', f'{install_name}-apt.sig')
        ssh(computer_name, 'sudo', 'apt-offline',
            'set', sig_filename, '--install-packages', *packages, _out=logger.debug)

        logger.info("Copy package signature to online computer.")
        if proxy != computer_name:
            copy_file(computer_name, proxy, sig_filename)

        logger.info("Downloading bundle...")
        bundle_filename = os.path.join('~/Downloads', f'{install_name}-apt-bundle.zip')
        ssh(proxy, 'sudo', 'apt-offline',
            'get', sig_filename, '--bundle', bundle_filename, _out=logger.debug)

        logger.info("Copy bundle to target computer.")
        if proxy != computer_name:
            copy_file(proxy, computer_name, bundle_filename)

        logger.info("Install bundle in target computer.")
        ssh(computer_name, 'sudo', 'apt-offline', 'install', bundle_filename, _out=logger.debug)
        ssh(computer_name, 'sudo', 'apt-get', 'install', *packages, _out=logger.debug)
        clean_install_files(computer_name, packages, online_computer)
    except ErrorReturnCode_1 as e:
        clean_install_files(computer_name, packages, online_computer)
        raise(e)

def computer_status(computer_name):
    computer_config = get_config(computer_name)

    status = 'up'
    try:
        ssh(computer_name, 'ls') # any ssh command sould make the job
    except ErrorReturnCode:
        status = 'down'

    online = is_online(computer_name) if status == 'up' else "N/A"

    return {
        'name': computer_name,
        'status': status,
        'online': online,
        'ip': computer_config['hostname']
    }

def status(computer_name=None):
    if computer_name:
        return computer_status(computer_name)
    computers_list = []
    for computer_name in get_list():
        computers_list.append(computer_status(computer_name))
    return computers_list