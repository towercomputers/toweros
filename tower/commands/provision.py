from argparse import ArgumentParser
import ipaddress
import os
import re

from tower.configs import default_config_dir, create_computer_config
from tower.burn import burn_image

def check_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-zA-Z0-9-]{1,15}$/', args.name):
        parser_error(message="Computer name invalid. Must be between one and 15 alphanumeric chars.")

    config_dir = args.config_dir or default_config_dir()
    config_file = os.path.join(config_dir, f'{args.name}.ini')
    if os.path.exists(config_file):
        parser_error("Computer name already used.")

    if not os.path.exists(args.sd_card):
        parser_error("sd-card path invalid.")
    
    if args.public_key:
        if not arg.private_key :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.public_key):
            parser_error("public_key path invalid.")
    
    if args.private_key:
        if not arg.public_key :
            parser_error("You must provide both keys or none.")
        if not os.path.exists(args.private_key):
            parser_error("private_key path invalid.")


def execute(args):
    config = create_computer_config(args)
    print(config)
    burn_image(config)