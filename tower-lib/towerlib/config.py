import os
import getpass

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
DESKTOP_FILES_DIR = os.path.expanduser('~/.local/share/applications')
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
HOST_ALPINE_BRANCH = "v3.18"
THINCLIENT_ALPINE_BRANCH = "v3.18"
