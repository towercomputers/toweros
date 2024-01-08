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
TOWER_VAR_DIR = "/var/towercomputers"
TOWER_BUILDS_DIR = "/var/towercomputers/builds"
TOWER_SSH_CONFIG_PATH = os.path.join(TOWER_DIR, 'config')
SSH_CONFIG_PATH = os.path.expanduser('~/.ssh/config')
KNOWN_HOSTS_PATH = os.path.expanduser('~/.ssh/known_hosts')
DESKTOP_FILES_DIR = os.path.expanduser('~/.local/share/applications')
APK_LOCAL_REPOSITORY = os.path.expanduser('~/packages/tower-apks')
RELEASES_URL = "https://raw.githubusercontent.com/towercomputers/toweros/dev/RELEASES"
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
HOST_ALPINE_BRANCH = "v3.19"
THINCLIENT_ALPINE_BRANCH = "v3.19"
ALPINE_RPI_URL = "https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/aarch64/alpine-rpi-3.19.0-aarch64.tar.gz"
ALPINE_RPI_CHECKSUM = "5621e7e597c3242605cd403a0a9109ec562892a6c8a185852b6b02ff88f5503c"
HOST_DEFAULT_PACKAGES = 'toweros-host'.split(" ")
THINCLIENT_DEFAULT_PACKAGES = 'toweros-thinclient alpine-base linux-lts xtables-addons-lts zfs-lts syslinux intel-media-driver libva-intel-driver linux-firmware linux-firmware-none'.split(" ")


VNC_VIEWER_CSS = """
headerbar {
    padding: 0px;
    margin: 0px;
    min-height: 0px;
    padding-left: 2px; /* same as childrens vertical margins for nicer proportions */
    padding-right: 2px;
    background-image: url("BACKGROUND_FILENAME");
    background-size: cover;
}

headerbar entry,
headerbar spinbutton,
headerbar button,
headerbar separator {
    margin-top: 0px; /* same as headerbar side padding for nicer proportions */
    margin-bottom: 0px;
    padding: 1px;
}

/* shrink ssd titlebars */
.default-decoration {
    min-height: 0; /* let the entry and button drive the titlebar size */
    padding: 0px;
    background-color: #FF0000;
}

.default-decoration .titlebutton {
    min-height: 0px; /* tweak these two props to reduce button size */
    min-width: 0px;
}

window.ssd headerbar.titlebar {
    padding-top: 0;
    padding-bottom: 0;
    min-height: 0;
}
"""
