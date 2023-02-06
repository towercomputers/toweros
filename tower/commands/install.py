import os
import re
from urllib.parse import urlparse

from tower import computers
from tower.configs import default_config_dir

def check_args(args, parser_error):
    # TODO: check package name format

    config = computers.get_computer_config(args.config_dir, args.computer_name[0])
    if config is None:
        parser_error("Unkown computer name.")
    elif config['online'] != 'true' and args.online_host is None:
        parser_error(f"{args.computer_name[0]} is not online. Please use the flag `--online-host`.")

    if args.online_host:
        config = computers.get_computer_config(args.config_dir, args.online_host)
        if config is None:
            parser_error("Unkown computer name for online host.")
        elif config['online'] != 'true':
            parser_error(f"{args.online_host} is not online.")

def execute(args):
    computers.install_package(args.config_dir, args.computer_name[0], args.package_name[0], args.online_host)