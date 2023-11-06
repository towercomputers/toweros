import os
import logging
import time
from ipaddress import ip_address, ip_network

from sshconf import read_ssh_config, empty_ssh_config_file
from sh import ssh, ErrorReturnCode, sed, touch, Command

from towerlib.utils import clitask

DEFAULT_SSH_USER = "tower"
TOWER_NETWORK_ONLINE = "192.168.2.0/24"
TOWER_NETWORK_OFFLINE = "192.168.3.0/24"
THIN_CLIENT_IP_ETH0 = "192.168.2.100"
THIN_CLIENT_IP_ETH1 = "192.168.3.100"
ROUTER_IP = "192.168.2.1"
ROUTER_HOSTNAME = "router"
FIRST_HOST_IP = 200 # 192.168.2.200 or 192.168.3.200

logger = logging.getLogger('tower')

class UnkownHost(Exception):
    pass

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
            f.write(directive + '\n\n')

def ssh_config():
    config_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'tower.conf')
    config = read_ssh_config(config_path) if os.path.exists(config_path) else empty_ssh_config_file()
    return config

def get(name):
    config = ssh_config()
    if name in config.hosts():
        return config.host(name)
    else:
        return None

def clean_known_hosts(ip):
    known_hosts_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'known_hosts')
    if os.path.exists(known_hosts_path):
        sed('-i', f'/{ip}/d', known_hosts_path)

def update_known_hosts(ip):
    known_hosts_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'known_hosts')
    if os.path.exists(known_hosts_path):
        sed('-i', f'/{ip}/d', known_hosts_path)
    else:
        touch(known_hosts_path)
    Command('sh')('-c', f'ssh-keyscan {ip} >> {known_hosts_path}')
    
@clitask("Updating Tower config file ~/.ssh/tower.conf...")
def update_config(name, ip, private_key_path):
    insert_include_directive()
    # get existing hosts
    config_path = os.path.join(os.path.expanduser('~'), '.ssh/', 'tower.conf')
    config = read_ssh_config(config_path) if os.path.exists(config_path) else empty_ssh_config_file()
    existing_hosts = config.hosts()
    # if name already used, update the IP
    if name in existing_hosts:
        config.set(name, Hostname=ip)
        config.save()
        return
    # if IP already used, update the name
    for host_name in existing_hosts:
        host = config.host(host_name)
        if host['hostname'] == ip:
            config.rename(host_name, name)
            config.set(name, IdentityFile=private_key_path)
            config.save()
            return
    # if not exists, create a new host
    config.add(name,
        Hostname=ip,
        User=DEFAULT_SSH_USER,
        IdentityFile=private_key_path,
        LogLevel="FATAL"
    )
    config.write(config_path)
    
def hosts():
    return ssh_config().hosts()

def exists(name):
    return name in hosts()

def is_online_host(name):
    if exists(name):
        ip = get(name)['hostname']
        network = ".".join(TOWER_NETWORK_ONLINE.split(".")[0:3]) + "."
        return ip.startswith(network)
    raise UnkownHost(f"Unknown host: {name}")

def is_up(name):
    if exists(name):
        try:
            ssh(name, 'ls') # Running a command over SSH command should tell us if the host is up.
        except ErrorReturnCode:
            return False
        return True
    raise UnkownHost(f"Unknown host: {name}")

def status(host_name = None):
    if host_name:
        host_config = get(host_name)
        host_status = 'up' if is_up(host_name) else 'down'
        online = is_online_host(host_name) if host_status == 'up' else "N/A"
        return {
            'name': host_name,
            'status': host_status,
            'online-host': online,
            'ip': host_config['hostname']
        }
    return [status(host_name) for host_name in hosts()]

def get_next_host_ip(tower_network, first=FIRST_HOST_IP):
    network = ".".join(tower_network.split(".")[0:3]) + "."
    for host_name in hosts():
        ip = get(host_name)['hostname']
        if ip.startswith(network):
            num = int(ip.split(".").pop())
            if num == first:
                first += 1
                return get_next_host_ip(tower_network, first=first + 1)
    return f"{network}{first}"

def try_to_update_known_hosts_until_success(ip):
    try:
        update_known_hosts(ip)
    except ErrorReturnCode:
        time.sleep(5)
        try_to_update_known_hosts_until_success(ip)

@clitask("Waiting for host to be ready...")
def wait_for_host_sshd(ip):
    try_to_update_known_hosts_until_success(ip)