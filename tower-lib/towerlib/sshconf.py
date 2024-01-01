import os
import logging
import time

from rich.console import Console
from rich.table import Table
from rich.text import Text
from sshconf import read_ssh_config, empty_ssh_config_file

from towerlib.utils.shell import ssh, ErrorReturnCode, sed, touch, Command
from towerlib.utils import clitask
from towerlib.utils.exceptions import DiscoveringTimeOut, UnkownHost, InvalidColor
from towerlib.__about__ import __version__
from towerlib.config import (
    SSH_CONFIG_PATH,
    TOWER_SSH_CONFIG_PATH,
    TOWER_DIR,
    DEFAULT_SSH_USER,
    FIRST_HOST_IP,
    KNOWN_HOSTS_PATH,
    COLORS,
    ROUTER_HOSTNAME,
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
        with open(SSH_CONFIG_PATH, 'r', encoding="UTF-8") as file_pointer:
            current_config = file_pointer.read()
        if directive not in current_config:
            with open(SSH_CONFIG_PATH, 'r+', encoding="UTF-8") as file_pointer:
                content = file_pointer.read()
                file_pointer.seek(0, 0)
                file_pointer.write(directive + '\n\n' + content)
    else:
        create_ssh_dir()
        with open(SSH_CONFIG_PATH, 'w', encoding="UTF-8") as file_pointer:
            file_pointer.write(directive + '\n\n')
        os.chmod(SSH_CONFIG_PATH, 0o600)


def ssh_config():
    return read_ssh_config(TOWER_SSH_CONFIG_PATH) if os.path.exists(TOWER_SSH_CONFIG_PATH) else empty_ssh_config_file()


def get(host):
    config = ssh_config()
    if host in config.hosts():
        return config.host(host)
    return None


def update_known_hosts(host, host_ip):
    if os.path.exists(KNOWN_HOSTS_PATH):
        sed('-i', f'/{host_ip}/d', KNOWN_HOSTS_PATH)
    else:
        create_ssh_dir()
        touch(KNOWN_HOSTS_PATH)
    for key_type in ['ecdsa', 'rsa', 'ed25519']:
        host_key_path = os.path.join(TOWER_DIR, 'hosts', host, f"ssh_host_{key_type}_key.pub")
        Command('sh')('-c', f'echo "{host_ip} $(cat {host_key_path})" >> {KNOWN_HOSTS_PATH}')


@clitask(f"Updating Tower config file {TOWER_SSH_CONFIG_PATH}...")
def update_config(host, host_ip, private_key_path):
    insert_include_directive()
    update_known_hosts(host, host_ip)
    # get existing hosts
    config = ssh_config()
    existing_hosts = config.hosts()
    # if name already used, update the IP
    if host in existing_hosts:
        config.set(host, Hostname=host_ip)
        config.set(host, IdentityFile=private_key_path)
        config.write(TOWER_SSH_CONFIG_PATH)
        return
    # if IP already used, update the name
    for existing_host in existing_hosts:
        existing_host_config = config.host(existing_host)
        if existing_host_config['hostname'] == host_ip:
            config.rename(existing_host, host)
            config.set(host, IdentityFile=private_key_path)
            config.write(TOWER_SSH_CONFIG_PATH)
            return
    # if not exists, create a new host
    config.add(host,
        Hostname=host_ip,
        User=DEFAULT_SSH_USER,
        IdentityFile=private_key_path,
        LogLevel="FATAL",
        ConnectTimeout=1,
    )
    if not os.path.exists(TOWER_DIR):
        os.makedirs(TOWER_DIR)
    config.write(TOWER_SSH_CONFIG_PATH)


@clitask("Updating ssh config with ConnectTimeout=1...")
def add_connect_timeout():
    config = ssh_config()
    for host in config.hosts():
        config.set(host, ConnectTimeout=1)
    config.write(TOWER_SSH_CONFIG_PATH)


def hosts():
    return ssh_config().hosts()


def exists(host):
    return host in hosts()


def is_online_host(host):
    if exists(host):
        return get_host_config_value(host, 'ONLINE') == 'true'
    raise UnkownHost(f"Unknown host: {host}")


def is_up(host):
    if exists(host):
        try:
            ssh(host, 'ls') # Running a command over SSH command should tell us if the host is up.
        except ErrorReturnCode:
            return False
        return True
    raise UnkownHost(f"Unknown host: {host}")


def status(host = None, full = True):
    if host:
        host_ssh_config = get(host)
        host_config = get_host_config(host)
        host_status = 'up' if is_up(host) else 'down'
        online = is_online_host(host)
        host_info = {
            'name': host,
            'status': host_status,
            'online-host': online,
            'ip': host_ssh_config['hostname'],
            'toweros-version': host_config.get('TOWEROS_VERSION', 'N/A'),
            'color': get_host_color_name(host),
        }
        if full:
            if host_status == 'up':
                inxi_info = ssh('-t', host, 'inxi', '-MIs', '-c', '0').strip()
                host_info['system'] = inxi_info[inxi_info.index('System: ') + 8:inxi_info.index(' details:')]
                memory_available = inxi_info[inxi_info.index('available: ') + 11:inxi_info.index(' used:')].strip()
                memory_used = inxi_info[inxi_info.index('used: ') + 6:inxi_info.index(' Init:')].strip()
                host_info['memory-usage'] = memory_used
                host_info['memory-total'] = memory_available
                host_info['cpu-usage'] = str(round(100 - float(ssh(host, 'mpstat').strip().split("\n")[-1].split(" ")[-1]), 2)) + "%"
                host_info['cpu-temperature'] = inxi_info[inxi_info.index('cpu: ') + 5:inxi_info.index(' mobo: ')].strip()
            else:
                host_info['system'] = 'N/A'
                host_info['memory-usage'] = 'N/A'
                host_info['memory-total'] = 'N/A'
                host_info['cpu-usage'] = 'N/A'
                host_info['cpu-temperature'] = 'N/A'
            host_info['packages-installed'] = ', '.join(get_installed_packages(host))
        return host_info
    return sorted([status(host, False) for host in hosts()], key=lambda k: k['name'])


def display_status(host = None):
    all_status = status(host)
    if host:
        all_status = [all_status]
    if len(all_status) == 0:
        print("No host found.")
        return
    table = Table(show_header=len(all_status) > 1)
    if len(all_status) > 1:
        headers = all_status[0].keys()
        for column in headers:
            table.add_column(column)
        for host_status in all_status:
            values = [str(value) for value in host_status.values()]
            values[0] = Text(values[0], style="bold")
            values[1] = Text(values[1], style="red" if values[1] == "down" else "green")
            online_color = "yellow" if values[2] == "True" else ("blue" if values[2] == "False" else "white")
            values[2] = Text(values[2], style=online_color)
            values[5] = Text(values[5], style=values[5].lower())
            table.add_row(*values)
    else:
        table.add_column("key")
        table.add_column("value")
        for key in all_status[0].keys():
            value = str(all_status[0][key])
            if key == "name":
                value = Text(value, style="bold")
            elif key == "status":
                value = Text(value, style="red" if value == "down" else "green")
            elif key == "online-host":
                value = Text(value, style="yellow" if value == "True" else ("blue" if value == "False" else "white"))
            elif key == "color":
                value = Text(value, style=value.lower())
            table.add_row(key, value)
    console = Console()
    console.print(table)


def get_next_host_ip(tower_network, first=FIRST_HOST_IP):
    network = ".".join(tower_network.split(".")[0:3]) + "."
    for host_name in hosts():
        host_ip = get(host_name)['hostname']
        if host_ip.startswith(network):
            num = int(host_ip.split(".").pop())
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
    with open(conf_path, 'r', encoding="UTF-8") as file_pointer:
        config_str = file_pointer.read()
    host_config = {}
    for line in config_str.strip().split("\n"):
        key = line[0:line.index('=')]
        value = line[line.index('=') + 2:-1]
        host_config[key] = value
    return host_config


def get_host_config_value(host, key):
    host_config = get_host_config(host)
    return host_config.get(key, None)


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


def get_installed_packages(host):
    apk_world = os.path.join(TOWER_DIR, 'hosts', host, 'world')
    if os.path.exists(apk_world):
        return open(apk_world, 'r', encoding="UTF-8").read().strip().split("\n")
    return []


def save_installed_packages(host, installed_packages):
    apk_world = os.path.join(TOWER_DIR, 'hosts', host, 'world')
    with open(apk_world, 'w', encoding="UTF-8") as file_pointer:
        file_pointer.write("\n".join(installed_packages))


@clitask("Syncing offline host time with `router`...")
def sync_time(offline_host = None):
    if not exists(ROUTER_HOSTNAME):
        return
    all_hosts = hosts() if not offline_host else [offline_host]
    offline_hosts =  [host for host in all_hosts if not is_online_host(host) and is_up(host)]
    if len(offline_hosts) == 0:
        return
    # update offline host time
    for host in offline_hosts:
        # pylint: disable=anomalous-backslash-in-string
        now = ssh(ROUTER_HOSTNAME, 'date +\%s').strip()
        ssh(host, f"sudo date -s @{now}")
    # update thinclient time
    now = ssh(ROUTER_HOSTNAME, 'date').strip()
    Command('sh')('-c', f"sudo date -s '{now}'")
