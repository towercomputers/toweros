import configparser
import os
import ipaddress
from random import randint
from argparse import ArgumentParser
import re

import rsa

DEFAULT_NETWORK = "192.168.0.0/24" # TODO: put in config file

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
    (public_key, private_key) = rsa.newkeys(2048)
    ssh_dir = default_ssh_dir()
    with open(os.path.join(ssh_dir, f'{name}_pub.pem'), 'wb') as p:
        p.write(public_key.save_pkcs1('PEM'))
    with open(os.path.join(ssh_dir, f'{name}_priv.pem'), 'wb') as p:
        p.write(private_key.save_pkcs1('PEM'))
    return f'{name}_pub.pem', f'{name}_priv.pem'


def create_computer_config(args):

    network = args.network or DEFAULT_NETWORK
    host = args.host or generate_random_ip(network)
    public_key, private_key = args.public_key, args.private_key
    if not public_key:
        public_key, private_key = generate_key_pair(args.name)

    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'name': args.name,
        'network': network,
        'host': host,
        'sd-card': args.sd_card,
        'public_key': public_key,
        'private_key': private_key,
    }

    config_dir = args.config_dir or default_config_dir()
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    config_file = os.path.join(config_dir, f'{args.name}.ini')
    with open(config_file, 'w') as f:
        config.write(f)
    
    return config['DEFAULT']
    