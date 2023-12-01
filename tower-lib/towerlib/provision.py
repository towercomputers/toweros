import os
import secrets
import logging
import tempfile

from passlib.hash import sha512_crypt
from sh import ssh_keygen, xz, ssh, cp, dd
from rich.prompt import Confirm
from rich.text import Text
from rich import print as rprint

from towerlib import utils, buildhost, sshconf, config, install
from towerlib.utils.exceptions import DiscoveringTimeOut, MissingEnvironmentValue, NetworkException, DiscoveringException

logger = logging.getLogger('tower')

def check_environment_value(key, value):
    if not value:
        raise MissingEnvironmentValue(f"Impossible to determine the {key}. Please use the option `--{key}`.")

def generate_key_pair(name):
    host_dir = os.path.join(config.TOWER_DIR, 'hosts', name)
    os.makedirs(host_dir, exist_ok=True)
    os.chmod(host_dir, 0o700)
    key_path = os.path.join(host_dir, 'id_ed25519')
    if os.path.exists(key_path):
        os.remove(key_path)
        os.remove(f'{key_path}.pub')
    ssh_keygen('-t', 'ed25519', '-C', name, '-f', key_path, '-N', "")
    return f'{key_path}.pub', key_path

def generate_luks_key(name):
    keys_path = os.path.join(config.TOWER_DIR, 'hosts', name, "crypto_keyfile.bin")
    os.makedirs(os.path.dirname(keys_path), exist_ok=True)
    dd('if=/dev/urandom', f'of={keys_path}', 'bs=512', 'count=4')

def generate_ssh_host_keys(name):
    for key_type in ['ecdsa', 'rsa', 'ed25519']:
        host_keys_path = os.path.join(config.TOWER_DIR, 'hosts', name, f"ssh_host_{key_type}_key")
        if os.path.exists(host_keys_path):
            os.remove(host_keys_path)
            os.remove(f'{host_keys_path}.pub')
        ssh_keygen('-t', key_type, '-f', host_keys_path, '-N', "")

@utils.clitask("Preparing host configuration...")
def prepare_host_config(args):
    name = args.name[0]
    # public key for ssh
    check_environment_value('public-key-path', args.public_key_path)
    with open(args.public_key_path, encoding="UTF-8") as f:
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
    online = 'true' if args.online or name == config.ROUTER_HOSTNAME else 'false'
    if name == config.ROUTER_HOSTNAME:
        wlan_ssid = args.wlan_ssid
        wlan_shared_key = utils.derive_wlan_key(args.wlan_ssid, args.wlan_password)
    else:
        wlan_ssid = ""
        wlan_shared_key = ""
    # determine thinclient IP and network
    if name == config.ROUTER_HOSTNAME or online == "true":
        tower_network = config.TOWER_NETWORK_ONLINE
        thin_client_ip = config.THIN_CLIENT_IP_ETH0
    else:
        tower_network = config.TOWER_NETWORK_OFFLINE
        thin_client_ip = config.THIN_CLIENT_IP_ETH1
    if name == config.ROUTER_HOSTNAME:
        host_ip =config.ROUTER_IP
    else:
        host_ip = sshconf.get_next_host_ip(tower_network)
    host_color = sshconf.color_code(args.color or sshconf.get_next_color_name())
    # return complete configuration
    return {
        'HOSTNAME': name,
        'USERNAME': config.DEFAULT_SSH_USER,
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
        'ROUTER_IP': config.ROUTER_IP,
        'COLOR': host_color,
        'INSTALLATION_TYPE': "install",
    }

@utils.clitask("Decompressing {0}...", sudo=True)
def decompress_image(image_path):
    out_file = image_path.replace('.xz', '')
    tmp_file = os.path.join(tempfile.gettempdir(), os.path.basename(out_file))
    xz('--stdout', '-d', image_path, _out=tmp_file)
    cp(tmp_file, out_file)
    return out_file

def prepare_host_image(image_arg):
    image_path = image_arg if image_arg and os.path.isfile(image_arg) else utils.find_host_image()
    if image_path:
        ext = image_path.split(".").pop()
        if ext == 'xz': # TODO: support more formats
            image_path = decompress_image(image_path)
    return image_path

def prepare_provision(args, upgrade=False):
    if upgrade:
        # use existing key pair
        private_key_path = os.path.join(config.TOWER_DIR, 'hosts', args.name[0], 'id_ed25519')
        # load configuration
        host_config = sshconf.get_host_config(args.name[0])
        host_config['INSTALLATION_TYPE'] = "upgrade"
    else:
        # generate key pair
        if not args.public_key_path:
            args.public_key_path, private_key_path = generate_key_pair(args.name[0])
        # generate luks key
        generate_luks_key(args.name[0])
        # generate ssh host keys
        generate_ssh_host_keys(args.name[0])
        # generate host configuration
        host_config = prepare_host_config(args)
    # determine target device
    boot_device = args.boot_device or utils.select_boot_device()
    check_environment_value('boot-device', boot_device)
    # find TowerOS-Host image
    image_path = prepare_host_image(args.image)
    check_environment_value('image', image_path)
    # inject image version in host config
    host_config['TOWEROS_VERSION'] = f"v{image_path.split('-')[-2]}"
    # return everything needed to provision the host
    return image_path, boot_device, host_config, private_key_path

@utils.clitask("Saving host configuration in {0}...")
def save_config_file(config_path, config_str):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w', encoding="UTF-8") as f:
        # we want the password in ~/.local/tower/hosts/<host>/tower.env for debugging purposes
        # codeql[py/clear-text-storage-sensitive-data]
        f.write(config_str)
    os.chmod(config_path, 0o600)

def save_host_config(host_config):
    config_path = os.path.join(config.TOWER_DIR, 'hosts', host_config['HOSTNAME'], 'tower.env')
    config_str = "\n".join([f"{key}='{value}'" for key, value in host_config.items()])
    save_config_file(config_path, config_str)

def check_network(online):
    ip = config.THIN_CLIENT_IP_ETH0 if online else config.THIN_CLIENT_IP_ETH1
    interface = 'eth0' if online else 'eth1'
    if not utils.interface_is_up(interface):
        raise NetworkException(f"Unable to connect to the network. Please make sure that the interface `{interface}` is up.")
    if not utils.is_ip_attached(interface, ip):
        raise NetworkException(f"Unable to connect to the network. Please make sure that the interface `{interface}` is attached to the IP `{ip}`.")

def display_pre_provision_warning(name, boot_device, upgrade):
    warning_message = f"WARNING: This will completely wipe the boot device `{boot_device}` plugged into the thin client."
    if not upgrade:
        warning_message += f"\nWARNING: This will completely wipe the root device plugged into the host `{name}`"
    else:
        warning_message += f"\nWARNING: This will completely re-install TowerOS on the host `{name}`. Your home directory will be preserved."
    warning_text = Text(warning_message, style='red')
    rprint(warning_text)

def display_pre_discovering_message():
    message = "Boot device ready.\n"
    message += "- Make sure that the host and thin client are connected to the same switch and to the correct interface and network "
    message += f"({config.TOWER_NETWORK_OFFLINE} for offline hosts and {config.TOWER_NETWORK_ONLINE} for online hosts).\n"
    message += "- Make sure that the host root drive is plugged into the host.\n"
    message += "- Remove the host boot drive from the thin client and insert it into the host being provisioned.\n"
    message += "- Turn on the host and wait for it to be discovered on the network... (This step can take up to 10 minutes under normal circumstances, depending mostly on the speed of the root device. If the host has still not discovered in that time period, you can troubleshoot by connecting a screen and a keyboard to it.\n"
    rprint(Text(message, style='green'))

def display_post_discovering_message(name, ip):
    if sshconf.is_up(name):
        message = f"Host ready with IP: {ip}\n"
    else:
        message = f"Host IP: {ip}\n"
    message += f"Access the host `{name}` with the command `$ ssh {name}`.\n"
    message += f"Install a package on `{name}` with the command `$ tower install {name} <package-name>`\n"
    message += f"Run a GUI application on `{name}` with the command `$ tower run {name} <package-name>`\n"
    message += "WARNING: For security reasons, make sure to remove the host boot device from the host."
    rprint(Text(message))

def wait_for_host(name, timeout):
    error_message = "Unable to confirm that the host is ready. To diagnose the problem, please refer to the troubleshooting documentation at https://toweros.org or run `bat ~/docs/installation.md`."
    try:
        sshconf.wait_for_host_sshd(name, timeout)
    except KeyboardInterrupt as exc1:
        logger.info("Discovering interrupted.")
        raise DiscoveringException(error_message) from exc1
    except DiscoveringTimeOut as exc2:
        logger.info("Discovering timed out.")
        raise DiscoveringException(error_message) from exc2

def prepare_thin_client(name, host_config, private_key_path):
    # save host configuration in Thin Client
    save_host_config(host_config)
    # prepare ssh config and known hosts
    sshconf.update_config(name, host_config['STATIC_HOST_IP'], private_key_path)
    # generate sfwbar widget
    utils.menu.generate_tower_widget()

@utils.clitask("Provisioning {0}...", timer_message="Host provisioned in {0}.", task_parent=True)
def provision(name, args, upgrade=False):
    # prepare provisioning
    image_path, boot_device, host_config, private_key_path = prepare_provision(args, upgrade)
    # check network
    if not args.force:
        check_network(host_config['ONLINE'] or name == config.ROUTER_HOSTNAME)
    # display warnings
    display_pre_provision_warning(name, boot_device, upgrade)
    # ask confirmation
    if not args.no_confirm and not Confirm.ask("Do you want to continue?", default=True):
        return
    # copy TowerOS-Host image to boot device
    buildhost.burn_image(image_path, boot_device, host_config, args.zero_device)
    # save necessary files in Thin Client
    if not upgrade:
        prepare_thin_client(name, host_config, private_key_path)
    # display pre discovering message
    display_pre_discovering_message()
    # wait for host to be ready
    if not args.no_wait:
        wait_for_host(name, args.timeout)
    # display post discovering message
    display_post_discovering_message(name, host_config['STATIC_HOST_IP'])
    # re-install packages
    if upgrade:
        if not args.no_wait:
            install.reinstall_all_packages(name)
        else:
            rprint(Text("WARNING: Packages were not re-installed. Please re-install them manually when the host is ready", style='red'))

@utils.clitask("Updating wlan credentials...")
def wlan_connect(ssid, password):
    psk = utils.derive_wlan_key(ssid, password)
    supplicant_path = "/etc/wpa_supplicant/wpa_supplicant.conf"
    cmd  = f"sudo echo 'network={{' | sudo tee {supplicant_path} && "
    cmd += f"sudo echo '    ssid=\"{ssid}\"'  | sudo tee -a  {supplicant_path} && "
    cmd += f"sudo echo '    psk={psk}'  | sudo tee -a {supplicant_path} && "
    cmd += f"sudo echo '}}' | sudo tee -a {supplicant_path}"
    ssh(config.ROUTER_HOSTNAME, cmd)
    ssh(config.ROUTER_HOSTNAME, "sudo rc-service wpa_supplicant restart")
