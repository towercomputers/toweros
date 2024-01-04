import os
import secrets
import logging
import tempfile
import json

from passlib.hash import sha512_crypt
from rich.prompt import Confirm, Prompt
from rich.text import Text
from rich import print as rprint

from towerlib.utils.shell import ssh_keygen, xz, ssh, cp, dd, scp, Command, doas
from towerlib import utils, buildhost, sshconf, config, install
from towerlib.utils.exceptions import (
    DiscoveringTimeOut,
    MissingEnvironmentValue,
    NetworkException,
    DiscoveringException,
    TowerException
)

logger = logging.getLogger('tower')


def check_environment_value(key, value):
    if not value:
        raise MissingEnvironmentValue(f"Impossible to determine the {key}. Please use the option `--{key}`.")


def generate_key_pair(host):
    host_dir = os.path.join(config.TOWER_DIR, 'hosts', host)
    os.makedirs(host_dir, exist_ok=True)
    os.chmod(host_dir, 0o700)
    key_path = os.path.join(host_dir, 'id_ed25519')
    if os.path.exists(key_path):
        os.remove(key_path)
        os.remove(f'{key_path}.pub')
    ssh_keygen('-t', 'ed25519', '-C', host, '-f', key_path, '-N', "")
    return f'{key_path}.pub', key_path


def generate_luks_key(host):
    keys_path = os.path.join(config.TOWER_DIR, 'hosts', host, "crypto_keyfile.bin")
    os.makedirs(os.path.dirname(keys_path), exist_ok=True)
    dd('if=/dev/urandom', f'of={keys_path}', 'bs=512', 'count=4')


def generate_ssh_host_keys(host):
    for key_type in ['ecdsa', 'rsa', 'ed25519']:
        host_keys_path = os.path.join(config.TOWER_DIR, 'hosts', host, f"ssh_host_{key_type}_key")
        if os.path.exists(host_keys_path):
            os.remove(host_keys_path)
            os.remove(f'{host_keys_path}.pub')
        ssh_keygen('-t', key_type, '-f', host_keys_path, '-N', "")


@utils.clitask("Preparing host configuration...")
def prepare_host_config(host, args):
    # public key for ssh
    check_environment_value('public-key-path', args.public_key_path)
    with open(args.public_key_path, encoding="UTF-8") as file_pointer:
        public_key = file_pointer.read().strip()
    # generate random password
    password = args.password or secrets.token_urlsafe(16)
    # gather locale informations
    keyboard_layout, keyboard_variant = utils.get_keymap()
    if args.keyboard_layout:
        keyboard_layout = args.keyboard_layout
    if args.keyboard_variant:
        keyboard_variant = args.keyboard_variant
    timezone = args.timezone or utils.get_timezone()
    lang = args.lang or utils.get_lang()
    # determine if online
    online = 'true' if args.online or host == config.ROUTER_HOSTNAME else 'false'
    if host == config.ROUTER_HOSTNAME:
        wlan_ssid = args.wlan_ssid
        wlan_shared_key = utils.derive_wlan_key(args.wlan_ssid, args.wlan_password)
    else:
        wlan_ssid = ""
        wlan_shared_key = ""
    # determine thinclient IP and network
    if host == config.ROUTER_HOSTNAME or online == "true":
        tower_network = config.TOWER_NETWORK_ONLINE
        thin_client_ip = config.THIN_CLIENT_IP_ETH0
    else:
        tower_network = config.TOWER_NETWORK_OFFLINE
        thin_client_ip = config.THIN_CLIENT_IP_ETH1
    if host == config.ROUTER_HOSTNAME:
        host_ip =config.ROUTER_IP
    else:
        host_ip = sshconf.get_next_host_ip(tower_network)
    host_color = sshconf.color_code(args.color or sshconf.get_next_color_name())
    # return complete configuration
    return {
        'HOSTNAME': host,
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
        'ALPINE_BRANCH': config.HOST_ALPINE_BRANCH,
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
        if ext == 'xz':
            image_path = decompress_image(image_path)
    return image_path


def find_no_root_device(host):
    disk_list = json.loads(ssh(host, "lsblk --json").strip())
    no_root_devices = []
    for device in disk_list['blockdevices']:
        if 'children' not in device:
            no_root_devices.append(f"/dev/{device['name']}")
            continue
        if device['children'][0]['name'] != 'lvmcrypt':
            no_root_devices.append(f"/dev/{device['name']}")
            continue
    return no_root_devices


def prepare_provision(host, args, upgrade=False):
    if upgrade:
        # use existing key pair
        private_key_path = os.path.join(config.TOWER_DIR, 'hosts', host, 'id_ed25519')
        # load configuration
        host_config = sshconf.get_host_config(host)
        host_config['INSTALLATION_TYPE'] = "upgrade"
        # determine target device
        no_root_devices = [args.boot_device] if  args.boot_device else find_no_root_device(host)
        if len(no_root_devices) != 1:
            raise TowerException(f"Unable to determine the boot device for host `{host}`. Please specify it with the option `--boot-device`.")
        boot_device = no_root_devices[0]
    else:
        # generate key pair
        if not args.public_key_path:
            args.public_key_path, private_key_path = generate_key_pair(host)
        # generate luks key
        generate_luks_key(host)
        # generate ssh host keys
        generate_ssh_host_keys(host)
        # generate host configuration
        host_config = prepare_host_config(host, args)
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
    with open(config_path, 'w', encoding="UTF-8") as file_pointer:
        # we want the password in ~/.local/tower/hosts/<host>/tower.env for debugging purposes
        #lgtm[py/clear-text-storage-sensitive-data]
        file_pointer.write(config_str)
    os.chmod(config_path, 0o600)


def save_host_config(host_config):
    config_path = os.path.join(config.TOWER_DIR, 'hosts', host_config['HOSTNAME'], 'tower.env')
    config_str = "\n".join([f"{key}='{value}'" for key, value in host_config.items()])
    save_config_file(config_path, config_str)


def check_network(online):
    host_ip = config.THIN_CLIENT_IP_ETH0 if online else config.THIN_CLIENT_IP_ETH1
    interface = 'eth0' if online else 'eth1'
    if not utils.interface_is_up(interface):
        raise NetworkException(f"Unable to connect to the network. Please make sure that the interface `{interface}` is up.")
    if not utils.is_ip_attached(interface, host_ip):
        raise NetworkException(f"Unable to connect to the network. Please make sure that the interface `{interface}` is attached to the IP `{host_ip}`.")


def display_pre_provision_warning(host, boot_device):
    warning_message = f"WARNING: This will completely wipe the boot device `{boot_device}` plugged into the thin client."
    warning_message += f"\nWARNING: This will completely wipe the root device plugged into the host `{host}`"
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


def display_post_discovering_message(host, host_ip):
    if sshconf.is_up(host):
        message = f"Host ready with IP: {host_ip}\n"
    else:
        message = f"Host IP: {host_ip}\n"
    message += f"Access the host `{host}` with the command `$ ssh {host}`.\n"
    message += f"Install a package on `{host}` with the command `$ tower install {host} <package-name>`\n"
    message += f"Run a GUI application on `{host}` with the command `$ tower run {host} <package-name>`\n"
    message += "WARNING: For security reasons, make sure to remove the host boot device from the host."
    rprint(Text(message))


def wait_for_hosts(hosts, timeout):
    error_message = f"Unable to confirm that the hosts {hosts} are ready. To diagnose the problem, please refer to the troubleshooting documentation at https://toweros.org or run `bat ~/docs/installation.md`."
    try:
        sshconf.wait_for_hosts_sshd(hosts, timeout)
    except KeyboardInterrupt as exc1:
        logger.info("Discovering interrupted.")
        raise DiscoveringException(error_message) from exc1
    except DiscoveringTimeOut as exc2:
        logger.info("Discovering timed out.")
        raise DiscoveringException(error_message) from exc2


def wait_for_host(host, timeout):
    wait_for_hosts([host], timeout)


def prepare_thin_client(host, host_config, private_key_path):
    # save host configuration in Thin Client
    save_host_config(host_config)
    if host_config['INSTALLATION_TYPE'] == "upgrade":
        return
    # prepare ssh config and known hosts
    sshconf.update_config(host, host_config['STATIC_HOST_IP'], private_key_path)
    # generate sfwbar widget
    utils.menu.generate_tower_widget()


@utils.clitask("Provisioning {0}...", timer_message="Host provisioned in {0}.", task_parent=True)
def provision(host, args):
    # prepare provisioning
    image_path, boot_device, host_config, private_key_path = prepare_provision(host, args, False)
    # check network
    if not args.force:
        check_network(host_config['ONLINE'] == 'true')
    # display warnings
    display_pre_provision_warning(host, boot_device)
    # ask confirmation
    if not args.no_confirm and not Confirm.ask("Do you want to continue?", default=True):
        return
    # copy TowerOS-Host image to boot device
    buildhost.burn_image(image_path, boot_device, host_config, args.zero_device)
    # save necessary files in Thin Client
    prepare_thin_client(host, host_config, private_key_path)
    # display pre discovering message
    display_pre_discovering_message()
    # wait for host to be ready
    if not args.no_wait:
        wait_for_host(host, args.timeout)
         # sync time
        if host_config['ONLINE'] == 'false':
            sshconf.sync_time(host)
    # display post discovering message
    display_post_discovering_message(host, host_config['STATIC_HOST_IP'])


def display_pre_upgrade_warning(host, boot_device):
    warning_message = f"WARNING: This will completely wipe the boot device `{boot_device}` plugged into the host `{host}`."
    warning_message += f"\nWARNING: This will completely re-install TowerOS on the host `{host}`. Your home directory will be preserved."
    warning_text = Text(warning_message, style='red')
    rprint(warning_text)


def get_upgradable_hosts():
    upgradable_hosts = []
    for host in sshconf.hosts():
        if not sshconf.is_up(host):
            continue
        no_root_devices = find_no_root_device(host)
        if len(no_root_devices) == 1:
            upgradable_hosts.append(host)
    return upgradable_hosts


@utils.clitask("Upgrading {0}...", timer_message="Host upgraded in {0}.", task_parent=True)
def upgrade_hosts(hosts, args):
    host_params = {}
    for host in hosts:
        if not sshconf.is_up(host):
            raise TowerException(f"`{host}` is down. Please start it first.")
        # prepare provisioning
        image_path, boot_device, host_config, private_key_path = prepare_provision(host, args, True)
        host_params[host] = {
            'image_path': image_path,
            'boot_device': boot_device,
            'host_config': host_config,
            'private_key_path': private_key_path,
        }
        # check network
        if not args.force:
            check_network(host_params[host]['host_config']['ONLINE'] == 'true')
        # display warnings
        display_pre_upgrade_warning(host, host_params[host]['boot_device'])

    # ask confirmation
    if not args.no_confirm and not Confirm.ask("Do you want to continue?", default=True):
        return

    for host in hosts:
        # copy TowerOS-Host image to boot device
        buildhost.burn_image_in_host(
            host,
            host_params[host]['image_path'],
            host_params[host]['boot_device'],
            host_params[host]['host_config'],
            args.zero_device
        )
        # save necessary files in Thin Client
        prepare_thin_client(
            host,
            host_params[host]['host_config'],
            host_params[host]['private_key_path']
        )

    # wait for host to be ready
    if not args.no_wait:
        wait_for_hosts(hosts, args.timeout)
        for host in hosts:
             # sync time
            if host_params[host]['host_config']['ONLINE'] == 'false':
                sshconf.sync_time(host)
            # re-install packages
            install.reinstall_all_packages(host)
    else:
        rprint(Text("WARNING: Packages were not re-installed. Please re-install them manually when hosts are ready", style='red'))


@utils.clitask("Downloading releases file...")
def get_latest_release_url():
    releases_filename = os.path.basename(config.RELEASES_URL)
    ssh(config.ROUTER_HOSTNAME, f"rm -f {releases_filename}")
    ssh(config.ROUTER_HOSTNAME, f"wget {config.RELEASES_URL}")
    latest_release_url = ssh(config.ROUTER_HOSTNAME, f"cat {releases_filename}").strip().split("\n")[0]
    return latest_release_url


@utils.clitask("Downloading latest release...")
def download_latest_release(latest_release_url):
    latest_release_filename = os.path.basename(latest_release_url)
    ssh(config.ROUTER_HOSTNAME, f"rm -f {latest_release_filename}")
    ssh(config.ROUTER_HOSTNAME, f"wget {latest_release_url}")
    scp(f"{config.ROUTER_HOSTNAME}:{latest_release_filename}", config.TOWER_DIR)
    Command('sh')('-c', f"sudo mv {config.TOWER_DIR}/{latest_release_filename} {config.TOWER_BUILDS_DIR}")
    return f"{config.TOWER_BUILDS_DIR}/{latest_release_filename}"


@utils.clitask("Upgrading Thin Client...", task_parent=True)
def upgrade_thinclient(args):
    # check if `router` is up
    install.can_install("thinclient")
    latest_release_url = get_latest_release_url()
    latest_release_path = download_latest_release(latest_release_url)
    install_device = args.install_device or utils.select_install_device()
    with doas:
        if args.zero_device:
            buildhost.zeroing_device(install_device)
        buildhost.copy_image_in_device(latest_release_path, install_device)
    warning_message = f"WARNING: This will completely wipe the install device `{install_device}` plugged into the thin client."
    warning_message += "\nWARNING: This will completely re-install TowerOS on the thin client. Your home directory will be preserved."
    rprint(Text(warning_message, style='red'))
    success_message = f"The `{install_device}` installation device is ready. Make sure it is the only one connected to the thin client and reboot."
    rprint(Text(success_message, style='green'))
    # ask confirmation
    if not args.no_confirm and not Confirm.ask("Do you want to reboot now?", default=True):
        return
    Command('sh')('-c', "sudo reboot")


@utils.clitask("Deprovisioning {0}...", timer_message="Host deprovisioned in {0}.", task_parent=True)
def deprovision(host, no_confirm=False):
    confirm_message = f"Are you sure you want to deprovision `{host}`? To confirm please enter the host name `{host}` and press enter"
    contirm_text = Text(confirm_message, style='red')
    confirm_name = Prompt.ask(contirm_text) if not no_confirm else host
    if confirm_name != host:
        rprint(Text(f"{confirm_name} != {host}. Deprovisioning aborted.", style='red'))
    else:
        sshconf.poweroff_host(host)
        sshconf.delete_host_config(host)
        utils.menu.generate_tower_widget()


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
