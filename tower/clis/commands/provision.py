import logging
import os
import re
import sys

from tower import provisioner, utils, sshconf

logger = logging.getLogger('tower')

def add_args(argparser):
    provision_parser = argparser.add_parser(
        'provision',
        help="""Command used to prepare the bootable SD Card needed to provision a host."""
    )
    provision_parser.add_argument(
        'name', 
        nargs=1,
        help="""Host's name. This name is used to install and run an application (Required)."""
    )
    provision_parser.add_argument(
        '-sd', '--sd-card', 
        help="""SD Card path.""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--public-key-path', 
        help="""Public key path used to access the host (Default: automatically generated and stored in the SD card and the local ~/.ssh/ folder).""",
        required=False
    )
    provision_parser.add_argument(
        '--private-key-path', 
        help="""Private key path used to access the host (Default: automatically generated and stored in the local ~/.ssh/ folder).""",
        required=False
    )
    provision_parser.add_argument(
        '--keymap', 
        help="""Keyboard layout code (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--timezone', 
        help="""Timezone of the host (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--lang', 
        help="""Language of the host (Default: same as the thin client)""",
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

def check_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-zA-Z0-9-]{1,15}$/', args.name[0]):
        parser_error(message="Host name invalid. Must be between one and 15 alphanumeric chars.")

    if sshconf.exists(args.name[0]):
        parser_error("Host name already used.")

    if args.sd_card:
        disk_list = utils.get_device_list()
        if args.sd_card not in disk_list:
            parser_error("sd-card path invalid.") 
        elif len(disk_list) == 1:
            parser_error("sd-card path invalid.") # can't right on the only disk
    
    if args.public_key_path:
        if not arg.private_key_path :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.public_key_path):
            parser_error("public_key path invalid.")
    
    if args.private_key_path:
        if not arg.public_key_path :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.private_key_path):
            parser_error("private_key path invalid.")
    
    if args.keymap:
        if re.match(r'^[a-zA-Z]{2}$', args.keymap) is None:
            parser_error(message="Keymap invalid. Must be 2 chars.")
    
    if args.timezone:
        if re.match(r'^[a-zA-Z-\ ]+\/[a-zA-Z-\ ]+$', args.timezone) is None:
            parser_error(message="Timezone invalide. Must be in <Area>/<City> format. eg. Europe/Paris.")
    
    # TODO: check args.lang validity
    
    if args.image:
        if not os.path.exists(args.image):
            parser_error(message="Invalid path for the image.")
        ext = args.image.split(".").pop()
        if os.path.exists(args.image) and ext not in ['img', 'xz']:
            parser_error(message="Invalid extension for image path (only `xz`or `img`).")


def execute(args):
    try:
        image_path, sd_card, host_config, private_key_path = provisioner.prepare_provision(args)
        provisioner.provision(args.name[0], image_path, sd_card, host_config, private_key_path)
    except provisioner.MissingEnvironmentValue as e:
        logger.error(e)
        sys.exit(1)