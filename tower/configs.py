import configparser
import os
import ipaddress
from random import randint
from argparse import ArgumentParser
import re
from sh import ssh_keygen

DEFAULT_RASPIOS_IMAGE = "https://downloads.raspberrypi.org/raspios_arm64/images/raspios_arm64-2022-09-26/2022-09-22-raspios-bullseye-arm64.img.xz"
DEFAULT_NETWORK = "192.168.0.0/24"
DEFAULT_SSH_USER = "tower"
DEFAULT_SSH_PORT = 22

def default_config_dir():
    home_path = os.path.expanduser('~')
    return os.path.join(home_path, '.config/', 'tower/')

def default_ssh_dir():
    home_path = os.path.expanduser('~')
    return os.path.join(home_path, '.ssh/')

def generate_random_ip(network):
    hosts = list(ipaddress.ip_network(network).hosts())
    return f'{hosts[randint(0, len(hosts) - 1)]}' # TODO: check if is used

def generate_key_pair(name):
    ssh_dir = default_ssh_dir()
    key_path = os.path.join(ssh_dir, f'{name}')
    ssh_keygen('-t', 'ed25519', '-C', name, '-f', key_path, '-N', "")
    return f'{key_path}.pub', key_path

def write_config_file(config, dir, filename):
    config_dir = dir or default_config_dir()
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    config_file = os.path.join(config_dir, f'{filename}')
    with open(config_file, 'w') as f:
        config.write(f)

def create_computer_config(args):
    network = args.network or DEFAULT_NETWORK
    host = args.host or generate_random_ip(network)
    public_key, private_key = args.public_key, args.private_key
    if not public_key:
        public_key, private_key = generate_key_pair(args.name)

    config = configparser.ConfigParser()
    config[configparser.DEFAULTSECT] = {
        'name': args.name,
        'network': network,
        'host': host,
        'sd-card': args.sd_card,
        'public-key': public_key,
        'private-key': private_key,
    }
    write_config_file(config, args.config_dir, f'{args.name}.ini')
    
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

    config[section]['default_network'] = config[section].get('default_network', DEFAULT_NETWORK)
    config[section]['default_ssh_user'] = config[section].get('default_ssh_user', DEFAULT_SSH_USER)
    config[section]['default_ssh_port'] = config[section].get('default_ssh_port', f'{DEFAULT_SSH_PORT}')
    config[section]['default_raspios_image'] = config[section].get('default_raspios_image', f'{DEFAULT_RASPIOS_IMAGE}')
    
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