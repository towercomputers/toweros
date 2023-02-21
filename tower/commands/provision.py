import logging
import os
import re
import sys

from tower import computers, osutils

logger = logging.getLogger('tower')

def check_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-zA-Z0-9-]{1,15}$/', args.name[0]):
        parser_error(message="Computer name invalid. Must be between one and 15 alphanumeric chars.")

    if computers.exists(args.name[0]):
        parser_error("Computer name already used.")

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
        if not os.path.exists(args.image) and not computers.is_valid_https_url(args.image):
            parser_error(message="Invalid path or url for the image.")
        ext = args.image.split(".").pop()
        if os.path.exists(args.image) and ext not in ['img', 'xz']:
            parser_error(message="Invalid extension for image path (only `xz`or `img`).")
        elif computers.is_valid_https_url(args.image) and ext not in ['xz']:
            parser_error(message="Invalid extension for image url (only `xz`).")

def execute(args):
    try:
        image_path, sd_card, firstrun_env, private_key_path = computers.prepare_provision(args)
        computers.provision(args.name[0], image_path, sd_card, firstrun_env, private_key_path)
    except computers.MissingEnvironmentValue as e:
        logger.error(e)
        sys.exit(1)
    
