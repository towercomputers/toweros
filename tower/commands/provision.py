from argparse import ArgumentParser
import ipaddress
import os
import re
import sys

from tower import computers, osutils, defaults, imager

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


def execute(args):
    if not args.public_key_path:
        args.public_key_path, private_key_path = computers.generate_key_pair(args.name[0])

    try:
        firstrun_env = computers.firstrun_env(args)
    except computers.MissingEnvironmentValue as e:
        logger.error(e)
        os.exit(1)

    sd_card = args.sd_card or osutils.select_sdcard_device()
    if not sd_card:
        logger.error("Impossible to determine the sd-card")
        os.exit(1)

    imager.burn_image(defaults.DEFAULT_OS_IMAGE, defaults.DEFAULT_OS_SHA256, sd_card, firstrun_env)

    print(f"SD Card ready. Please insert the SD-Card in the Raspberry-PI, turn it on and wait for it to be detected on the network.")
    
    ip = computers.discover_ip(args.name[0])
    computers.update_config(args.name[0], ip, private_key_path)
