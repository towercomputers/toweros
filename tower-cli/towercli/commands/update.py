import logging
import os
import re
import sys

from towerlib import provision, utils, sshconf

logger = logging.getLogger('tower')

def add_args(argparser):
    provision_parser = argparser.add_parser(
        'update',
        help="""Command used to prepare the bootable device needed to update a host."""
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
        '--image', 
        help="""Image path""",
        required=False,
    )
    provision_parser.add_argument(
        '--ifname', 
        help="""Network interface (Default: first interface starting by 'e') """,
        required=False,
    )

def check_args(args, parser_error):
    if not sshconf.exists(args.name[0]):
        parser_error("Host name not found.")

    if args.boot_device:
        disk_list = utils.get_device_list()
        if args.boot_device not in disk_list:
            parser_error("boot device path invalid.") 
        elif len(disk_list) == 1:
            parser_error("boot device path invalid.") # can't right on the only disk

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

def execute(args):
    try:
        provision.provision(args.name[0], args, update=True)
    except provision.MissingEnvironmentValue as e:
        logger.error(e)
        sys.exit(1)
