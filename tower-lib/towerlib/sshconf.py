import os
import logging
import time

from sshconf import read_ssh_config, empty_ssh_config_file

from towerlib.utils.shell import ssh, ErrorReturnCode, sed, touch, Command
from towerlib.utils import clitask
from towerlib.utils.exceptions import DiscoveringTimeOut, UnkownHost, InvalidColor
from towerlib.__about__ import __version__
from towerlib.config import (
    SSH_CONFIG_PATH,
    TOWER_SSH_CONFIG_PATH,
    TOWER_DIR,
    TOWER_NETWORK_ONLINE,
    DEFAULT_SSH_USER,
    FIRST_HOST_IP,
    KNOWN_HOSTS_PATH,
    COLORS
)

logger = logging.getLogger('tower')

def create_ssh_dir():
    ssh_dir = os.path.dirname(SSH_CONFIG_PATH)
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
        os.chmod(ssh_dir, 0o700)

def insert_include_directive():
    directive = f"Include {TOWER_SSH_CONFIG_PATH}"
    if os.path.exists(SSH_CONFIG_PATH):
        with open(SSH_CONFIG_PATH, 'r', encoding="UTF-8") as f:
            current_config = f.read()
        if directive not in current_config:
            with open(SSH_CONFIG_PATH, 'r+', encoding="UTF-8") as f:
                content = f.read()
                f.seek(0, 0)
                f.write(directive + '\n\n' + content)
    else:
        create_ssh_dir()
        with open(SSH_CONFIG_PATH, 'w', encoding="UTF-8") as f:
            f.write(directive + '\n\n')
        os.chmod(SSH_CONFIG_PATH, 0o600)

def ssh_config():
    return read_ssh_config(TOWER_SSH_CONFIG_PATH) if os.path.exists(TOWER_SSH_CONFIG_PATH) else empty_ssh_config_file()

def get(host):
    config = ssh_config()
    if host in config.hosts():
        return config.host(host)
    return None

def update_known_hosts(host, ip):
    if os.path.exists(KNOWN_HOSTS_PATH):
        sed('-i', f'/{ip}/d', KNOWN_HOSTS_PATH)
    else:
        create_ssh_dir()
        touch(KNOWN_HOSTS_PATH)
    for key_type in ['ecdsa', 'rsa', 'ed25519']:
        host_key_path = os.path.join(TOWER_DIR, 'hosts', host, f"ssh_host_{key_type}_key.pub")
        Command('sh')('-c', f'echo "{ip} $(cat {host_key_path})" >> {KNOWN_HOSTS_PATH}')

@clitask(f"Updating Tower config file {TOWER_SSH_CONFIG_PATH}...")
def update_config(host, ip, private_key_path):
    insert_include_directive()
    update_known_hosts(host, ip)
    # get existing hosts
    config = ssh_config()
    existing_hosts = config.hosts()
    # if name already used, update the IP
    if host in existing_hosts:
        config.set(host, Hostname=ip)
        config.set(host, IdentityFile=private_key_path)
        config.write(TOWER_SSH_CONFIG_PATH)
        return
    # if IP already used, update the name
    for existing_host in existing_hosts:
        existing_host_config = config.host(existing_host)
        if existing_host_config['hostname'] == ip:
            config.rename(existing_host, host)
            config.set(host, IdentityFile=private_key_path)
            config.write(TOWER_SSH_CONFIG_PATH)
            return
    # if not exists, create a new host
    config.add(host,
        Hostname=ip,
        User=DEFAULT_SSH_USER,
        IdentityFile=private_key_path,
        LogLevel="FATAL"
    )
    if not os.path.exists(TOWER_DIR):
        os.makedirs(TOWER_DIR)
    config.write(TOWER_SSH_CONFIG_PATH)

def hosts():
    return ssh_config().hosts()

def exists(host):
    return host in hosts()

def is_online_host(host):
    if exists(host):
        ip = get(host)['hostname']
        network = ".".join(TOWER_NETWORK_ONLINE.split(".")[0:3]) + "."
        return ip.startswith(network)
    raise UnkownHost(f"Unknown host: {host}")

def is_up(host):
    if exists(host):
        try:
            ssh(host,  '-o', 'ConnectTimeout=2', 'ls') # Running a command over SSH command should tell us if the host is up.
        except ErrorReturnCode:
            return False
        return True
    raise UnkownHost(f"Unknown host: {host}")

def status(host = None):
    if host:
        host_ssh_config = get(host)
        host_config = get_host_config(host)
        host_status = 'up' if is_up(host) else 'down'
        online = is_online_host(host) if host_status == 'up' else "N/A"
        return {
            'name': host,
            'status': host_status,
            'online-host': online,
            'ip': host_ssh_config['hostname'],
            'version': host_config.get('TOWEROS_VERSION', 'N/A')
        }
    return [status(host) for host in hosts()]

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

@clitask("Waiting for host to be ready...")
def wait_for_host_sshd(host, timeout):
    start_time = time.time()
    while not is_up(host):
        duration = time.time() - start_time
        if timeout and duration > timeout:
            raise DiscoveringTimeOut("Host discovery timeout")
        time.sleep(3)

def get_host_config(host):
    conf_path = os.path.join(TOWER_DIR, 'hosts', host, "tower.env")
    with open(conf_path, 'r', encoding="UTF-8") as f:
        config_str = f.read()
    host_config = {}
    for line in config_str.strip().split("\n"):
        key = line[0:line.index('=')]
        value = line[line.index('=') + 2:-1]
        host_config[key] = value
    return host_config

def get_version():
    versions = {
        "thinclient": __version__,
        "hosts": {}
    }
    for host_name in hosts():
        host_config = get_host_config(host_name)
        versions['hosts'][host_name] = host_config.get('TOWEROS_VERSION', 'N/A')
    return versions

def color_name_list():
    return [color[1] for color in COLORS]

def color_code(host):
    for color in COLORS:
        if color[1] == host:
            return color[0]
    raise InvalidColor(f"Invalid color name: {host}")

def color_hex(code_or_name):
    for color in COLORS:
        if isinstance(code_or_name, int):
            if color[0] == code_or_name:
                return color[2]
        if isinstance(code_or_name, str):
            if color[1] == code_or_name:
                return color[2]
    raise InvalidColor(f"Invalid color code or name: {code_or_name}")

def get_next_color_name():
    return COLORS[len(hosts()) % len(COLORS)][1]

def get_host_color_name(host):
    host_config = get_host_config(host)
    host_color_code = int(host_config.get('COLOR', COLORS[0][0]))
    for color in COLORS:
        if color[0] == host_color_code:
            return color[1]
    return COLORS[0][1]

def get_hex_host_color(host):
    host_config = get_host_config(host)
    host_color_code= int(host_config.get('COLOR', COLORS[0][0]))
    return color_hex(host_color_code)
