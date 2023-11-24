import os
import logging
import time
import getpass
from ipaddress import ip_address, ip_network

from sshconf import read_ssh_config, empty_ssh_config_file
from sh import ssh, ErrorReturnCode, sed, touch, Command

from towerlib.utils import clitask
from towerlib.utils.exceptions import DiscoveringTimeOut, UnkownHost, InvalidColor
from towerlib.__about__ import __version__

DEFAULT_SSH_USER = getpass.getuser()
TOWER_NETWORK_ONLINE = "192.168.2.0/24"
TOWER_NETWORK_OFFLINE = "192.168.3.0/24"
THIN_CLIENT_IP_ETH0 = "192.168.2.100"
THIN_CLIENT_IP_ETH1 = "192.168.3.100"
ROUTER_IP = "192.168.2.1"
ROUTER_HOSTNAME = "router"
FIRST_HOST_IP = 200 # 192.168.2.200 or 192.168.3.200
TOWER_DIR = os.path.expanduser('~/.local/tower')
TOWER_SSH_CONFIG_PATH = os.path.join(TOWER_DIR, 'config')
SSH_CONFIG_PATH = os.path.expanduser('~/.ssh/config')
KNOWN_HOSTS_PATH = os.path.expanduser('~/.ssh/known_hosts')
COLORS = [
    [39, "White", "ffffff"],
    [31, "Red", "cc0000"],
    [32, "Green", "4e9a06"],
    [33, "Yellow", "c4a000"],
    [34, "Blue", "729fcf"],
    [35, "Magenta", "75507b"],
    [36, "Cyan", "06989a"],
    [37, "Light gray", "d3d7cf"],
    [91, "Light red", "ef2929"],
    [92, "Light green", "8ae234"],
    [93, "Light yellow", "fce94f"],
    [94, "Light blue", "32afff"],
    [95, "Light magenta", "ad7fa8"],
    [96, "Light cyan", "34e2e2"],
]

logger = logging.getLogger('tower')

def create_ssh_dir():
    ssh_dir = os.path.dirname(SSH_CONFIG_PATH)
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
        os.chmod(ssh_dir, 0o700)

def insert_include_directive():
    directive = f"Include {TOWER_SSH_CONFIG_PATH}"
    if os.path.exists(SSH_CONFIG_PATH):
        with open(SSH_CONFIG_PATH, 'r') as f:
            current_config = f.read()
        if directive not in current_config:
            with open(SSH_CONFIG_PATH, 'r+') as f:
                content = f.read()
                f.seek(0, 0)
                f.write(directive + '\n\n' + content)
    else:
        create_ssh_dir()
        with open(SSH_CONFIG_PATH, 'w') as f:
            f.write(directive + '\n\n')
        os.chmod(SSH_CONFIG_PATH, 0o600)

def ssh_config():
    return read_ssh_config(TOWER_SSH_CONFIG_PATH) if os.path.exists(TOWER_SSH_CONFIG_PATH) else empty_ssh_config_file()

def get(name):
    config = ssh_config()
    if name in config.hosts():
        return config.host(name)
    else:
        return None

def update_known_hosts(name, ip):
    if os.path.exists(KNOWN_HOSTS_PATH):
        sed('-i', f'/{ip}/d', KNOWN_HOSTS_PATH)
    else:
        create_ssh_dir()
        touch(KNOWN_HOSTS_PATH)
    for key_type in ['ecdsa', 'rsa', 'ed25519']:
        host_key_path = os.path.join(TOWER_DIR, 'hosts', name, f"ssh_host_{key_type}_key.pub")
        Command('sh')('-c', f'echo "{ip} $(cat {host_key_path})" >> {KNOWN_HOSTS_PATH}')
    
@clitask(f"Updating Tower config file {TOWER_SSH_CONFIG_PATH}...")
def update_config(name, ip, private_key_path):
    insert_include_directive()
    update_known_hosts(name, ip)
    # get existing hosts
    config = ssh_config()
    existing_hosts = config.hosts()
    # if name already used, update the IP
    if name in existing_hosts:
        config.set(name, Hostname=ip)
        config.set(name, IdentityFile=private_key_path)
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
    if not os.path.exists(TOWER_DIR):
        os.makedirs(TOWER_DIR)
    config.write(TOWER_SSH_CONFIG_PATH)

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
            ssh(name,  '-o', 'ConnectTimeout=2', 'ls') # Running a command over SSH command should tell us if the host is up.
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

@clitask("Waiting for host to be ready...")
def wait_for_host_sshd(name, timeout):
    start_time = time.time()
    while not is_up(name):
        duration = time.time() - start_time
        if timeout > 0 and duration > timeout:
            raise DiscoveringTimeOut("Host discovering timeout")
        time.sleep(3)

def get_host_config(name):
    conf_path = os.path.join(TOWER_DIR, 'hosts', name, "tower.env")
    with open(conf_path, 'r') as f:
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

def color_code(name):
    for color in COLORS:
        if color[1] == name:
            return color[0]
    raise InvalidColor(f"Invalid color name: {name}")

def color_hex(code_or_name):
    for color in COLORS:
        if type(code_or_name) == int:
            if color[0] == code_or_name:
                return color[2]
        if type(code_or_name) == str:
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

def get_hex_host_color(host):
    host_config = get_host_config(host)
    host_color_code= int(host_config.get('COLOR', COLORS[0][0]))
    return color_hex(host_color_code)