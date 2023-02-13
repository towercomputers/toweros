import sys
import os
import re
from urllib.parse import urlparse

from tower import computers

def check_args(args, parser_error):
    name = args.computer_name[0]
    config = computers.get_config(name)
    if config is None:
        parser_error("Unkown computer name.")
    elif not computers.is_online(name) and args.online_host is None:
        parser_error(f"{name} is not online. Please use the flag `--online-host`.")
    
    for pkg_name in args.packages:
        if re.match(r'^[a-z0-9]{1}[a-z0-9\-\+\.]+$', pkg_name) is None:
            parser_error(f"Invalid package name:{pkg_name}")

    if args.online_host:
        config = computers.get_config(args.online_host)
        if config is None:
            parser_error("Unkown computer name for online host.")
        elif not computers.is_online(args.online_host):
            parser_error(f"{args.online_host} is not online.")

def execute(args):
    try:
        computers.install(args.computer_name[0], args.packages, args.online_host)
    except Exception as e:
        sys.exit(e)