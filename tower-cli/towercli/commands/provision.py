import logging
import os
import re
import sys

from towerlib import provision, utils, sshconf

logger = logging.getLogger('tower')

def add_args(argparser):
    provision_parser = argparser.add_parser(
        'provision',
        help="""Command used to prepare the bootable device needed to provision a host."""
    )
    provision_parser.add_argument(
        'name', 
        nargs=1,
        help="""Host's name. This name is used to install and run an application (Required)."""
    )
    provision_parser.add_argument(
        '-bd', '--boot-device', 
        help="""SD Card or USB key path.""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--zero-device', 
        help="""Zeroing device before copying image (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--no-confirm', 
        help="""Don't ask confirmation (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--public-key-path', 
        help="""Public key path used to access the host (Default: automatically generated and stored in the boot device and the local ~/.ssh/ folder).""",
        required=False
    )
    provision_parser.add_argument(
        '--private-key-path', 
        help="""Private key path used to access the host (Default: automatically generated and stored in the local ~/.ssh/ folder).""",
        required=False
    )
    provision_parser.add_argument(
        '--keyboard-layout', 
        help="""Keyboard layout code (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--keyboard-variant', 
        help="""Keyboard variant code (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--timezone', 
        help="""Timezone of the host. eg. Europe/Paris (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--lang', 
        help="""Language of the host. eg. en_US (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--online', 
        help="""Set wifi connection (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--offline',
        help="""Don't set wifi connection (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--wlan-ssid', 
        help="""Wifi SSID (Default: same as the connection currently used by the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--wlan-password', 
        help="""Wifi password (Default: same as the connection currently used by the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--image', 
        help="""Image path""",
        required=False,
    )
    provision_parser.add_argument(
        '--ifname', 
        help="""Network interface (Default: first interface starting by 'e') """,
        required=False,
    )
    provision_parser.add_argument(
        '--force', 
        help="""Overwrite existing host (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--no-wait', 
        help="""Do not wait for the host to be ready (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--timeout', 
        help="""Maximum wait time for the host to be ready in seconds (Default: 600)""",
        type=int,
        required=False,
        default=600
    )

def check_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-z0-9-]{1,15}$/', args.name[0]):
        parser_error(message="Host name invalid. Must be between one and 15 minuscule alphanumeric chars.")

    if sshconf.exists(args.name[0]) and not args.force:
        parser_error(f"Host name already used. Please use the flag `--force` to overwrite it or `tower update {args.name[0]}`to update it.")

    if args.boot_device:
        disk_list = utils.get_device_list()
        if args.boot_device not in disk_list:
            parser_error("boot device path invalid.") 
        elif len(disk_list) == 1:
            parser_error("boot device path invalid.") # can't right on the only disk

    if args.public_key_path:
        if not args.private_key_path :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.public_key_path):
            parser_error("public_key path invalid.")

    if args.private_key_path:
        if not args.public_key_path :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.private_key_path):
            parser_error("private_key path invalid.")

    if args.keyboard_layout:
        if re.match(r'^[a-zA-Z]{2}$', args.keyboard_layout) is None:
            parser_error(message="Keyboard layout invalid. Must be 2 chars.")
    
    if args.keyboard_variant:
        if re.match(r'^[a-zA-Z0-9-_]{2,32}$', args.keyboard_variant) is None:
            parser_error(message="Keyboard layout invalid. Must be alphanumeric between 2 and 32 chars.")

    if args.timezone:
        if re.match(r'^[a-zA-Z-\ ]+\/[a-zA-Z-\ ]+$', args.timezone) is None:
            parser_error(message="Timezone invalid. Must be in <Area>/<City> format. eg. Europe/Paris.")

    if args.lang:
        if  re.match(r'^[a-z]{2}_[A-Z]{2}$', args.lang) is None:
            parser_error(message="Lang invalid. Must be in <lang>_<country> format. eg. en_US.")

    if args.image:
        if not os.path.exists(args.image):
            parser_error(message="Invalid path for the image.")
        ext = args.image.split(".").pop()
        if os.path.exists(args.image) and ext not in ['img', 'xz']:
            parser_error(message="Invalid extension for image path (only `xz`or `img`).")

    if args.ifname:
        interaces = utils.get_interfaces()
        if args.ifname not in interaces:
            parser_error(message=f"Invalid network interface. Must be one of: {', '.join(interaces)}")
    
    if args.name[0] == "thinclient":
        parser_error(message="You can't use `thinclient` as host name.")
    elif args.name[0] == sshconf.ROUTER_HOSTNAME:
        if not args.wlan_ssid:
            parser_error(message="You must provide a wifi SSID for the router.")
        if not args.wlan_password:
            parser_error(message="You must provide a wifi password for the router.")
    else:
        if args.online == args.offline:
            parser_error(message="You must use one and only one of the argument `--online` and `--offline`.")
        if args.online:
            if not sshconf.exists(sshconf.ROUTER_HOSTNAME) and not args.force:
                parser_error(message=f"`{sshconf.ROUTER_HOSTNAME}` host not found. Please provision it first.")


def execute(args):
    try:
        provision.provision(args.name[0], args)
    except provision.MissingEnvironmentValue as e:
        logger.error(e)
        sys.exit(1)
