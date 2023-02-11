import sys
import os
import re
from urllib.parse import urlparse

from tower import computers

def check_args(args, parser_error):
    # TODO: check package name format
    name = args.computer_name[0]
    config = computers.get_config(name)
    if config is None:
        parser_error("Unkown computer name.")
    elif not computers.is_online(name) and args.online_host is None:
        parser_error(f"{name} is not online. Please use the flag `--online-host`.")

    if args.online_host:
        config = computers.get_config(args.online_host)
        if config is None:
            parser_error("Unkown computer name for online host.")
        elif not computers.is_online(args.online_host):
            parser_error(f"{args.online_host} is not online.")

def execute(args):
    try:
        computers.install_package(args.computer_name[0], args.package_name[0], args.online_host)
    except Exception as e:
        sys.exit(e)