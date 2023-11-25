import logging
import os
import sys

from towerlib import provision, utils, sshconf

logger = logging.getLogger('tower')

def add_args(argparser):
    provision_parser = argparser.add_parser(
        'upgrade',
        help="""Prepare the boot device needed to upgrade a host."""
    )
    provision_parser.add_argument(
        'name', 
        nargs=1,
        help="""Host's name, used to refer to the host when performing other actions (Required)"""
    )
    provision_parser.add_argument(
        '-bd', '--boot-device', 
        help="""Path to target SD card or USB drive""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--zero-device', 
        help="""Zero the target device before copying the installation image to it. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--no-confirm', 
        help="""Don't ask for confirmation. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--image', 
        help="""Path to installation image""",
        required=False,
    )
    provision_parser.add_argument(
        '--ifname', 
        help="""Network interface (Default: first interface starting with 'e') """,
        required=False,
    )

def check_args(args, parser_error):
    if not sshconf.exists(args.name[0]):
        parser_error("Host not found in TowerOS configuration file.")

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

def execute(args):
    try:
        provision.provision(args.name[0], args, upgrade=True)
    except provision.MissingEnvironmentValue as e:
        logger.error(e)
        sys.exit(1)
