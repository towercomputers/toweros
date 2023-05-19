import os
import logging
import time
from ipaddress import ip_address, ip_network

from sshconf import read_ssh_config, empty_ssh_config_file
from sh import ssh, ErrorReturnCode, avahi_resolve, sed, touch, Command

from tower.utils import clitask

DEFAULT_SSH_USER = "tower"

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

def sed_escape(str):
    escaped = str
    for c in "\$.*/[]^":
        escaped = escaped.replace(c, f'\{c}')
    return escaped
    
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

def is_host(ip, private_key_path, network):
    if ip_address(ip) not in ip_network(network):
        return False
    try:
        update_known_hosts(ip)
        ssh('-i', private_key_path, f'{DEFAULT_SSH_USER}@{ip}', 'ls') # Running a command over SSH command should tell us if the key is correct.
    except ErrorReturnCode:
        clean_known_hosts(ip)
        return False
    return True

def discover_ip(name, private_key_path, network):
    result = avahi_resolve('-4', '-n', f'{name}.local')
    if result != "":
        ip = result.strip().split("\t").pop()
        if is_host(ip, private_key_path, network):
            return ip
    time.sleep(1)
    return discover_ip(name, private_key_path, network)

@clitask("Discovering {0}...")
def discover(name, private_key_path, network):
    return discover_ip(name, private_key_path, network)

def discover_and_update(name, private_key_path, host_config):
    ip = discover(name, private_key_path, host_config['TOWER_NETWORK'])
    update_config(name, ip, private_key_path)
    return ip

def is_connected(name):
    if exists(name):
        status = ssh(name, 'cat', '/sys/class/net/wlan0/operstate').strip()
        if status == "up":
            return True
        return False
    raise UnkownHost(f"Unknown host: {name}")

def is_online_host(name):
    if exists(name):
        try:
            ssh(name, 'ls', '/etc/wpa_supplicant/wpa_supplicant.conf')
            return True
        except ErrorReturnCode:
            return False
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
        connected = is_connected(host_name) if online == True else False
        return {
            'name': host_name,
            'status': host_status,
            'online-host': online,
            'connected': connected,
            'ip': host_config['hostname']
        }
    return [status(host_name) for host_name in hosts()]
