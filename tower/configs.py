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

DEFAULT_RASPIOS_IMAGE = "https://downloads.raspberrypi.org/raspios_arm64/images/raspios_arm64-2022-09-26/2022-09-22-raspios-bullseye-arm64.img.xz"
DEFAULT_SSH_USER = "tower"
DEFAULT_SSH_PORT = 22

class MissingConfigValue(Exception):
    pass

def default_config_dir():
    home_path = os.path.expanduser('~')
    return os.path.join(home_path, '.config/', 'tower/')

def read_config(dir, filename):
    config = configparser.ConfigParser()
    config_dir = dir or default_config_dir()
    config_file = os.path.join(config_dir, filename)
    if os.path.exists(config_file):
        config.read(config_file)
    return config

def write_config(dir, filename, config):
    config_dir = dir or default_config_dir()
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    config_file = os.path.join(config_dir, filename)
    with open(config_file, 'w') as f:
        config.write(f)

def check_missing_value(key, value):
    if not value:
        raise MissingConfigValue(f"Impossible to determine the {key}. Please use the option --{key}.")

##########################
# General configuration  #
##########################

def get_tower_config(dir):
    config = configparser.ConfigParser()
    section = configparser.DEFAULTSECT
    config = read_config(dir, 'tower.ini')
    config[section]['default-ssh-user'] = config[section].get('default-ssh-user', DEFAULT_SSH_USER)
    config[section]['default-ssh-port'] = config[section].get('default-ssh-port', f'{DEFAULT_SSH_PORT}')
    config[section]['default-raspios-image'] = config[section].get('default-raspios-image', f'{DEFAULT_RASPIOS_IMAGE}')
    return config[section]

###############################
# Applications configurations #
###############################

# TODO: use one file for all applications
def create_application_config(args):
    config = configparser.ConfigParser()
    config[configparser.DEFAULTSECT] = {
        'name': args.name,
        'alias': args.alias,
        'path': args.path,
        'apt-packages': args.apt_packages or "",
        'local-apt-packages': args.local_apt_packages or "",
    }
    write_config(args.config_dir, f'{args.name}.{args.alias}.ini', config)
    return config[configparser.DEFAULTSECT]

def get_application_config(dir, name, alias):
    config_dir = dir or default_config_dir()
    config_file = os.path.join(config_dir, f'{name}.{alias}.ini')
    config = configparser.ConfigParser()
    config.read(config_file)
    return config[configparser.DEFAULTSECT]