import binascii
import configparser
import os
import ipaddress
from random import randint
from argparse import ArgumentParser
import re
import secrets
from io import StringIO
from datetime import datetime
import sys

from passlib.hash import sha512_crypt
from sh import ssh, scp, ErrorReturnCode_1
from sshconf import read_ssh_config, empty_ssh_config_file

from tower import osutils
from tower import configs


def firstrun_script(args):
    print("Generating firstrun.sh...")
    name = args.name[0]

    public_key_path, private_key_path = args.public_key_path, args.private_key_path
    if not public_key_path:
        public_key_path, private_key_path = osutils.generate_key_pair(name)
    
    with open(public_key_path) as f:
        public_key = f.read().strip()

    password = secrets.token_urlsafe(16)
    
    keymap = args.keymap or osutils.get_keymap()
    timezone = args.timezone or osutils.get_timezone()

    if args.online:
        online = 'true'
        wlan_ssid = args.wlan_ssid or osutils.get_connected_ssid()
        configs.check_missing_value('wlan-ssid', wlan_ssid)
        wlan_password = args.wlan_password or osutils.get_ssid_password(wlan_ssid)
        configs.check_missing_value('wlan-password', wlan_password)
        wlan_country = args.wlan_country or osutils.find_wlan_country(wlan_ssid)
        configs.check_missing_value('wlan-country', wlan_country)
    else:
        online = 'false'
        wlan_ssid, wlan_password, wlan_country = '', '', ''
  
    vars = {
        'NAME': name,
        'PUBLIC_KEY': public_key,
        'ENCRYPTED_PASSWORD': sha512_crypt.hash(password),
        'KEYMAP': keymap,
        'TIMEZONE': timezone,
        'ONLINE': online,
        'WLAN_SSID': wlan_ssid,
        'WLAN_PASSWORD': wlan_password,
        'WLAN_COUNTRY': wlan_country,
        'USER': configs.DEFAULT_SSH_USER
    }
    with open('scripts/firstrun.sh', 'r') as f:
        template = Template(f.read())
    script = template.safe_substitute(vars)
    return script


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


def update_config(name, ip):
    insert_include_directive()

    config_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'tower.conf')
    key_path = os.path.join(os.path.expanduser('~'), '.ssh/', name)
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
            config.set(name, IdentityFile=key_path)
            config.save()
            return
    
    config.add(name,
        Hostname=ip,
        User=config.DEFAULT_SSH_USER,
        IdentityFile=key_path,
        StrictHostKeyChecking="no",
        LogLevel="FATAL"
    )
    config.write(config_path)
    print(f"{config_path} updated")


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
    raise Exception("Unknown computer") # TODO: custom exception


def discover_ip(computer_name):
    buf = StringIO()
    arp('-a', _out=buf)
    result = buf.getvalue()
    lines = result.split("\n")
    for line in lines:
        if line.startswith(f'{computer_name}.local'):
            ip = line.split("(")[1].split(")")[0]
            print(f"IP found: {ip}")
            return ip
    print(f"Fail to discover the IP for {computer_name}. Retrying in 10 seconds")
    time.sleep(10)
    return discover_ip(computer_name)


def refresh_config(computer_name):
    ip = discover_ip(params['name'])
    update_config(params['name'], ip)


# TODO: make all these function more robust

def copy_file(computer_name_src, computer_name_dest, filename):
    scp('-3', f'{computer_name_src}:{filename}', f'{computer_name_dest}:{filename}')


def install_package(computer_name, package_name, online_computer=None):
    proxy = computer_name if online_computer is None else online_computer

    try:
        print("Generate package signature in target computer.")
        sig_filename = os.path.join('~/Downloads', f'{package_name}-apt.sig')
        ssh(computer_name, 'sudo', 'apt-offline',
            'set', sig_filename, '--install-packages', package_name, _out=sys.stdin)

        print("Copy package signature to online computer.")
        if proxy != computer_name:
            copy_file(computer_name, proxy, sig_filename, _out=sys.stdin)

        print("Downloading bundle...")
        bundle_filename = os.path.join('~/Downloads', f'{package_name}-apt-bundle.zip')
        ssh(proxy, 'sudo', 'apt-offline',
            'get', sig_filename, '--bundle', bundle_filename, _out=sys.stdin)

        print("Copy bundle to target computer.")
        if proxy != computer_name:
            copy_file(proxy, computer_name, bundle_filename)

        print("Install bundle in target computer.")
        ssh(computer_name, 'sudo', 'apt-offline', 'install', bundle_filename, _out=sys.stdin)
        ssh(computer_name, 'sudo', 'apt-get', 'install', package_name, _out=sys.stdin)
    except ErrorReturnCode_1 as e:
        sys.exit(e)
    # TODO: check if ok and remove the dpkg file

    
