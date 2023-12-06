import logging
import os
import re
import sys

from towerlib import provision, utils, sshconf, config

logger = logging.getLogger('tower')

def provision_parser(argparser):
    help_message = "Prepare the bootable device needed to provision a host"
    return argparser.add_parser(
        'provision',
        help=help_message, description=help_message
    )

def upgrade_parser(argparser):
    help_message = "Prepare the bootable device needed to upgrade a host"
    return argparser.add_parser(
        'upgrade',
        help=help_message, description=help_message
    )

def add_args(argparser, upgrade=False):
    parser = upgrade_parser(argparser) if upgrade else provision_parser(argparser)

    parser.add_argument(
        'name',
        nargs=1,
        help="""Host's name, used to refer to the host when performing other actions (Required)"""
    )
    parser.add_argument(
        '--boot-device',
        help="""Path to virtual device for the SD card or USB drive""",
        required=False,
        default=""
    )
    parser.add_argument(
        '--zero-device',
        help="""Zero the target device before copying the installation image to it. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--no-confirm',
        help="""Don't ask for confirmation. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--image',
        help="""Path to installation image""",
        required=False,
    )
    parser.add_argument(
        '--ifname',
        help="""Network interface (Default: `eth0` for online host, `eth1` for offline host) """,
        required=False,
    )
    parser.add_argument(
        '--no-wait',
        help="""Do not wait for the host to be ready (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--timeout',
        help="""Maximum wait time for the host to be ready, in seconds. Specify `0` for no limit. (Default: 600)""",
        type=int,
        required=False,
        default=600
    )
    parser.add_argument(
        '--force',
        help="""Overwrite the configuration for an existing host (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )

    if not upgrade:
        parser.add_argument(
            '--public-key-path',
            help="""Path to public key used to access the host (Default: automatically generated and stored on the boot device and locally in `~/.local/tower/hosts/`)""",
            required=False
        )
        parser.add_argument(
            '--private-key-path',
            help="""Path to private key used to access the host (Default: automatically generated and stored locally in `~/.local/tower/hosts/`)""",
            required=False
        )
        parser.add_argument(
            '--password',
            help="""Password to access the host (Default: automatically generated and stored locally in `~/.local/tower/hosts/`)""",
            required=False
        )
        parser.add_argument(
            '--keyboard-layout',
            help="""Keyboard layout code (Default: same as that of the thin client)""",
            required=False,
            default=""
        )
        parser.add_argument(
            '--keyboard-variant',
            help="""Keyboard variant code (Default: same as that of the thin client)""",
            required=False,
            default=""
        )
        parser.add_argument(
            '--timezone',
            help="""Timezone of the host. e.g. `Europe/Paris` (Default: same as that of the thin client)""",
            required=False,
            default=""
        )
        parser.add_argument(
            '--lang',
            help="""Language of the host. e.g. `en_US` (Default: same as that of the thin client)""",
            required=False,
            default=""
        )
        parser.add_argument(
            '--online',
            help="""Host *WILL* be able to access the Internet via the router. (Default: False)""",
            required=False,
            action='store_true',
            default=False
        )
        parser.add_argument(
            '--offline',
            help="""Host will *NOT* be able to access the Internet via the router. (Default: False)""",
            required=False,
            action='store_true',
            default=False
        )
        parser.add_argument(
            '--wlan-ssid',
            help="""WiFi SSID (Default: same as that currently in use by the thin client)""",
            required=False,
            default=""
        )
        parser.add_argument(
            '--wlan-password',
            help="""WiFi password (Default: same as that currently currently in use by the thin client)""",
            required=False,
            default=""
        )
        next_color_name = sshconf.get_next_color_name()
        parser.add_argument(
            '--color',
            help=f"Color used for shell prompt and GUI. (Default: sequentially from the list, next: {next_color_name})",
            type=str,
            required=False,
            choices=sshconf.color_name_list(),
            default=next_color_name
        )

def check_common_args(args, parser_error):
    if args.boot_device:
        disk_list = utils.get_device_list()
        if args.boot_device not in disk_list:
            parser_error("Boot device path invalid.")
        elif len(disk_list) == 1:
            parser_error("Boot device path invalid.") # can't write to the only disk
    if args.image:
        if not os.path.exists(args.image):
            parser_error(message="Invalid path to the image.")
        ext = args.image.split(".").pop()
        if os.path.exists(args.image) and ext not in ['img', 'xz']:
            parser_error(message="Invalid extension for image path. Must be either `xz`or `img`.")
    if args.ifname:
        interaces = utils.get_interfaces()
        if args.ifname not in interaces:
            parser_error(message=f"Invalid network interface. Must be one of: {', '.join(interaces)}.")

def check_locale_args(args, parser_error):
    if args.keyboard_layout:
        if re.match(r'^[a-zA-Z]{2}$', args.keyboard_layout) is None:
            parser_error(message="Keyboard layout invalid. Must be 2 characters long.")
    if args.keyboard_variant:
        if re.match(r'^[a-zA-Z0-9-_]{2,32}$', args.keyboard_variant) is None:
            parser_error(message="Keyboard layout invalid. Must be alphanumeric between 2 and 32 characters in length.")
    if args.timezone:
        if re.match(r'^[a-zA-Z-\ ]+\/[a-zA-Z-\ ]+$', args.timezone) is None:
            parser_error(message="Timezone invalid. Must be in `<Area>/<City>` format, e.g. `Europe/Paris`.")
    if args.lang:
        if  re.match(r'^[a-z]{2}_[A-Z]{2}$', args.lang) is None:
            parser_error(message="Language invalid. Must be in `<lang>_<country>` format, e.g. `en_US`.")

def check_keys_args(args, parser_error):
    if args.public_key_path:
        if not args.private_key_path :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.public_key_path):
            parser_error("Public_key path invalid.")

    if args.private_key_path:
        if not args.public_key_path :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.private_key_path):
            parser_error("Private_key path invalid.")

def check_provision_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-z0-9-]{1,15}$/', args.name[0]):
        parser_error(message="Host name is invalid. Must be between 1 and 15 lowercase alphanumeric characters.")
    if sshconf.exists(args.name[0]) and not args.force:
        parser_error(f"Host name already in use. Please use the flag `--force` to overwrite it or `tower upgrade {args.name[0]}` to upgrade it.")
    if args.name[0] == "thinclient":
        parser_error(message="You can't use `thinclient` as host name.")
    elif args.name[0] == config.ROUTER_HOSTNAME:
        if not args.wlan_ssid:
            parser_error(message="You must provide a WiFi SSID for the router.")
        if not args.wlan_password:
            parser_error(message="You must provide a WiFi password for the router.")
    else:
        if args.online == args.offline:
            parser_error(message="You must specify either `--online` or `--offline`, but not both.")
        if args.online:
            if not sshconf.exists(config.ROUTER_HOSTNAME) and not args.force:
                parser_error(message=f"`{config.ROUTER_HOSTNAME}` host not found. Please provision it first.")
    check_keys_args(args, parser_error)
    check_locale_args(args, parser_error)

def check_args(args, parser_error):
    check_common_args(args, parser_error)
    check_provision_args(args, parser_error)

def execute(args):
    try:
        provision.provision(args.name[0], args)
    except provision.MissingEnvironmentValue as e:
        logger.error(e)
        sys.exit(1)
