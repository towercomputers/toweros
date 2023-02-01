import configparser
import os
import ipaddress
from random import randint
from argparse import ArgumentParser
import re
import secrets
from sh import ssh_keygen

DEFAULT_RASPIOS_IMAGE = "https://downloads.raspberrypi.org/raspios_arm64/images/raspios_arm64-2022-09-26/2022-09-22-raspios-bullseye-arm64.img.xz"
DEFAULT_SSH_USER = "tower"
DEFAULT_SSH_PORT = 22

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

def create_computer_config(args):
    public_key, private_key = args.public_key, args.private_key
    if not public_key:
        public_key, private_key = generate_key_pair(args.name)

    config = configparser.ConfigParser()
    config[configparser.DEFAULTSECT] = {
        'name': args.name,
        'sd-card': args.sd_card,
        'public-key': public_key,
        'private-key': private_key,
        'password': secrets.token_urlsafe(16),
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