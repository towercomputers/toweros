import os
import secrets
import logging
from datetime import datetime

from passlib.hash import sha512_crypt
from sh import ssh_keygen, xz

from tower import utils
from tower import buildhost
from tower import sshconf

logger = logging.getLogger('tower')

class MissingEnvironmentValue(Exception):
    pass

def check_environment_value(key, value):
    if not value:
        raise MissingEnvironmentValue(f"Impossible to determine the {key}. Please use the option --{key}.")

def generate_key_pair(name):
    ssh_dir = os.path.join(os.path.expanduser('~'), '.ssh/')
    key_path = os.path.join(ssh_dir, f'{name}')
    if os.path.exists(key_path):
        os.remove(key_path)
        os.remove(f'{key_path}.pub')
    ssh_keygen('-t', 'ed25519', '-C', name, '-f', key_path, '-N', "")
    return f'{key_path}.pub', key_path

def prepare_wifi_parameters(args):
    online, wlan_ssid, wlan_password = 'false', '', ''
    if args.online:
        online = 'true'
        wlan_ssid = args.wlan_ssid or utils.get_connected_ssid()
        check_environment_value('wlan-ssid', wlan_ssid)
        if args.wlan_password:
            wlan_password = utils.derive_wlan_key(wlan_ssid, args.wlan_password)
        else:
            wlan_password = utils.get_wpa_psk()
        check_environment_value('wlan-password', wlan_password)
    return online, wlan_ssid, wlan_password

def get_network_infos(args):
    interface = args.ifname if args.ifname else utils.find_wired_interface()
    check_environment_value('ifname', interface)
    thin_client_ip = utils.get_interface_ip(interface)
    tower_network = utils.get_interface_network(interface)
    if not thin_client_ip or not tower_network:
        raise MissingEnvironmentValue(f"Impossible to determine the thin client IP/Network. Please ensure you are connected to the network on `{interface}`.")
    return thin_client_ip, tower_network

@utils.clitask("Preparing host configuration...")
def prepare_host_config(args):
    name = args.name[0]
    # public key for ssh
    check_environment_value('public-key-path', args.public_key_path)
    with open(args.public_key_path) as f:
        public_key = f.read().strip()
    # generate random password
    password = secrets.token_urlsafe(16)
    # gather locale informations
    keyboard_layout, keyboard_variant = utils.get_keymap()
    if args.keyboard_layout:
        keyboard_layout = args.keyboard_layout
    if args.keyboard_variant:
        keyboard_variant = args.keyboard_variant
    timezone = args.timezone or utils.get_timezone()
    lang = args.lang or utils.get_lang()
    # determine wifi parameters
    online, wlan_ssid, wlan_password = prepare_wifi_parameters(args)
    # determine thinclient IP and network
    thin_client_ip, tower_network = get_network_infos(args)
    # return complete configuration
    return {
        'HOSTNAME': name,
        'USERNAME': sshconf.DEFAULT_SSH_USER,
        'PUBLIC_KEY': public_key,
        'PASSWORD': password,
        'PASSWORD_HASH': sha512_crypt.hash(password),
        'KEYBOARD_LAYOUT': keyboard_layout,
        'KEYBOARD_VARIANT': keyboard_variant,
        'TIMEZONE': timezone,
        'LANG': lang,
        'ONLINE': online,
        'WLAN_SSID': wlan_ssid,
        'WLAN_SHARED_KEY': wlan_password,
        'THIN_CLIENT_IP': thin_client_ip,
        'TOWER_NETWORK': tower_network,
    }

@utils.clitask("Decompressing {0}...")
def decompress_image(image_path):
    out_file = image_path.replace('.xz', '')
    xz('--stdout', '-d', image_path, _out=out_file)
    return out_file

def prepare_host_image(image_arg):
    image_path = image_arg if image_arg and os.path.isfile(image_arg) else utils.find_host_image()
    if image_path:
        ext = image_path.split(".").pop()
        if ext == 'xz': # TODO: support more formats
            image_path = decompress_image(image_path)
    return image_path

def prepare_provision(args):
    # generate key pair
    if not args.public_key_path:
        args.public_key_path, private_key_path = generate_key_pair(args.name[0])
    # generate host configuration
    host_config = prepare_host_config(args)
    # determine target device
    sd_card = args.sd_card or utils.select_sdcard_device()
    check_environment_value('sd-card', sd_card)
    # find TowerOS-Host image
    image_path = prepare_host_image(args.image)
    check_environment_value('image', image_path)
    # return everything needed to provision the host
    return image_path, sd_card, host_config, private_key_path

@utils.clitask("Saving host configuration in {0}...")
def save_config_file(config_path, config_str):
    with open(config_path, 'w') as f:
        f.write(config_str)

def save_host_config(config):
    config_filename = f"{config['HOSTNAME']}-{datetime.now().strftime('%Y%m%d%H%M%S')}.env"
    config_path = os.path.join(os.path.expanduser('~'), '.config', 'tower', config_filename)
    config_str = "\n".join([f"{key}='{value}'" for key, value in config.items()])
    save_config_file(config_path, config_str)

@utils.clitask("Provisioning {0}...", timer_message="Host provisioned in {0}.", task_parent=True)
def provision(name, args):
    image_path, sd_card, host_config, private_key_path = prepare_provision(args)
    save_host_config(host_config)
    buildhost.burn_image(image_path, sd_card, host_config)
    ip = sshconf.discover_and_update(name, private_key_path, host_config)
    logger.info(f"Host found at: {ip}")
    logger.info(f"Access the host `{name}` with the command `$ ssh {name}`.")
    logger.info(f"Install a package on `{name}` with the command `$ tower install {name} <package-name>`")
    logger.info(f"Run a GUI application on `{name}` with the command `$ tower run {name} <package-name>`")
