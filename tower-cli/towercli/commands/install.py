import re

from towerlib import sshconf
from towerlib import install

def add_args(argparser):
    install_parser = argparser.add_parser(
        'install',
        help="""Command used to install an application in a host prepared with the `provision` command."""
    )

    install_parser.add_argument(
        'host_name', 
        help="""Host name where to install the package (Required).""",
        nargs=1
    )
    install_parser.add_argument(
        'packages', 
        help="""Package(s) to install (Required).""",
        nargs='+'
    )

def check_args(args, parser_error):
    name = args.host_name[0]
    config = sshconf.get(name)

    if config is None and name != "thinclient":
        parser_error("Unkown host name.")

    for pkg_name in args.packages:
        if re.match(r'^[a-z0-9]{1}[a-z0-9\-\+\.]+$', pkg_name) is None:
            parser_error(f"Invalid package name:{pkg_name}")

def execute(args):
    install.install_packages(args.host_name[0], args.packages)