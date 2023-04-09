import os
import logging
import time
from ipaddress import ip_address, ip_network

from sshconf import read_ssh_config, empty_ssh_config_file
from sh import ssh, ErrorReturnCode, avahi_resolve, sed

DEFAULT_SSH_USER = "tower"

logger = logging.getLogger('tower')

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
    logger.info(f"{config_path} updated")

def hosts():
    return ssh_config().hosts()

def exists(name):
    return name in hosts()

def discover_ip(name, network):
    result = avahi_resolve('-4', '-n', f'{name}.local')
    if result != "":
        ip = result.strip().split("\t").pop()
        if ip_address(ip) in ip_network(network):
            logger.info(f"IP found: {ip}")
            return ip
    logger.info(f"Fail to discover the IP for {name}. Retrying in 10 seconds.")
    time.sleep(10)
    return discover_ip(name, network)

def discover_and_update(name, private_key_path, network):
    ip = discover_ip(name, network)
    clean_known_hosts(ip)
    update_config(name, ip, private_key_path)

def is_online(name):
    if exists(name):
        try:
            ssh(name, 'ping', '-c', '1', '8.8.8.8')
            return True
        except ErrorReturnCode:
            return False
    raise UnkownHost(f"Unknown host: {name}")

def status(host_name = None):
    if host_name:
        host_config = get(host_name)
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
    return [status(host_name) for host_name in hosts()]