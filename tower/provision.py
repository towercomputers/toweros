import os
import secrets
import logging
from datetime import datetime

from passlib.hash import sha512_crypt
from sh import ssh_keygen, xz, ssh
from rich.prompt import Confirm
from rich.text import Text

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
    # determine if online
    online = 'true' if args.online or name == sshconf.ROUTER_HOSTNAME else 'false'
    if name == sshconf.ROUTER_HOSTNAME:
        wlan_ssid = args.wlan_ssid
        wlan_shared_key = utils.derive_wlan_key(args.wlan_ssid, args.wlan_password)
    else:
        wlan_ssid = ""
        wlan_shared_key = ""
    # determine thinclient IP and network
    if name == sshconf.ROUTER_HOSTNAME or online == "true":
        tower_network = sshconf.TOWER_NETWORK_ONLINE
        thin_client_ip = sshconf.THIN_CLIENT_IP_ETH0
    else:
        tower_network = sshconf.TOWER_NETWORK_OFFLINE
        thin_client_ip = sshconf.THIN_CLIENT_IP_ETH1
    if name == sshconf.ROUTER_HOSTNAME:
        host_ip =sshconf.ROUTER_IP
    else:
        host_ip = sshconf.get_next_host_ip(tower_network)
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
        'WLAN_SHARED_KEY': wlan_shared_key,
        'THIN_CLIENT_IP': thin_client_ip,
        'TOWER_NETWORK': tower_network,
        'STATIC_HOST_IP': host_ip,
        'ROUTER_IP': sshconf.ROUTER_IP
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
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
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
    confirmation = Text(f"Are you sure you want to completely wipe {sd_card}?", style='red')
    if args.no_confirm or Confirm.ask(confirmation):
        save_host_config(host_config)
        del(host_config['PASSWORD'])
        buildhost.burn_image(image_path, sd_card, host_config, args.zero_device)
        sshconf.wait_for_host_sshd(host_config['STATIC_HOST_IP'])
        sshconf.update_config(name, host_config['STATIC_HOST_IP'], private_key_path)
        utils.menu.prepare_xfce_menu()
        logger.info(f"Host ready with IP: {host_config['STATIC_HOST_IP']}")
        logger.info(f"Access the host `{name}` with the command `$ ssh {name}`.")
        logger.info(f"Install a package on `{name}` with the command `$ tower install {name} <package-name>`")
        logger.info(f"Run a GUI application on `{name}` with the command `$ tower run {name} <package-name>`")

@utils.clitask("Updating wlan credentials...")
def wlan_connect(ssid, password):
    psk = utils.derive_wlan_key(ssid, password)
    supplicant_path = "/etc/wpa_supplicant/wpa_supplicant.conf"
    cmd  = f"sudo echo 'network={{' | sudo tee {supplicant_path} && "
    cmd += f"sudo echo '    ssid=\"{ssid}\"'  | sudo tee -a  {supplicant_path} && "
    cmd += f"sudo echo '    psk={psk}'  | sudo tee -a {supplicant_path} && "
    cmd += f"sudo echo '}}' | sudo tee -a {supplicant_path}"
    ssh(sshconf.ROUTER_HOSTNAME, cmd)
    ssh(sshconf.ROUTER_HOSTNAME, "sudo rc-service wpa_supplicant restart")