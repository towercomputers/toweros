from argparse import ArgumentParser
import ipaddress
import os
import re
import sys

from tower import computers, osutils
from tower.configs import (
    default_config_dir,
    get_tower_config, 
    MissingConfigValue,
)
from tower.imager import burn_image

def check_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-zA-Z0-9-]{1,15}$/', args.name[0]):
        parser_error(message="Computer name invalid. Must be between one and 15 alphanumeric chars.")

    if computers.exists(args.name[0]):
        parser_error("Computer name already used.")

    if args.sd_card and not os.path.exists(args.sd_card):
        parser_error("sd-card path invalid.") # TODO: check is a disk
    
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
    
    # TODO: check format for keymap, timezone, and wlan-country


def execute(args):
    try:
        firstrun_script = computers.firstrun_script(args)
    except MissingConfigValue as e:
        sys.exit(e)

    sd_card = args.sd_card or osutils.select_sdcard_device()
    configs.check_missing_value('sd-card', sd_card)

    burn_image(configs.DEFAULT_OS_IMAGE, sd_card, firstrun_script)

    print(f"SD Card ready. Please unmount and insert the SD-Card in the Raspberry-PI, turn it on and wait for it to be detected on the network.")
    computers.refresh_config(args.name[0])