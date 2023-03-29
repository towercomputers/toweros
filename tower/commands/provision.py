import logging
import os
import re
import sys

from tower import hosts, osutils

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
        '--wlan-country', 
        help="""Wifi country (Default: same as the connection currently used by the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--image', 
        help="""Image path or URL""",
        required=True, # TODO: make optional when `tower` image will be online
    )

def check_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-zA-Z0-9-]{1,15}$/', args.name[0]):
        parser_error(message="Host name invalid. Must be between one and 15 alphanumeric chars.")

    if hosts.exists(args.name[0]):
        parser_error("Host name already used.")

    if args.sd_card:
        disk_list = osutils.get_device_list()
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
    
    if args.wlan_country:
        if re.match(r'^[a-zA-Z]{2}$', args.wlan_country) is None:
            parser_error(message="Wlan country invalid. Must be 2 chars.")
    
    if args.image:
        if not os.path.exists(args.image) and not hosts.is_valid_https_url(args.image):
            parser_error(message="Invalid path or url for the image.")
        ext = args.image.split(".").pop()
        if os.path.exists(args.image) and ext not in ['img', 'xz']:
            parser_error(message="Invalid extension for image path (only `xz`or `img`).")
        elif hosts.is_valid_https_url(args.image) and ext not in ['xz']:
            parser_error(message="Invalid extension for image url (only `xz`).")

def execute(args):
    try:
        image_path, sd_card, firstrun_env, private_key_path = hosts.prepare_provision(args)
        hosts.provision(args.name[0], image_path, sd_card, firstrun_env, private_key_path)
    except hosts.MissingEnvironmentValue as e:
        logger.error(e)
        sys.exit(1)
    
