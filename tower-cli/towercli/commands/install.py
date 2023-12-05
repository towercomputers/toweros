import re

from towerlib import sshconf
from towerlib import install

def add_args(argparser):
    help_message = "Install an application on a host with APK"
    install_parser = argparser.add_parser(
        'install',
        help=help_message, description=help_message
    )
    install_parser.add_argument(
        'host_name',
        help="""Host to install the package on (Required)""",
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
        parser_error("Unkown host.")

    for pkg_name in args.packages:
        if re.match(r'^[a-z0-9]{1}[a-z0-9\-\+\.]+$', pkg_name) is None:
            parser_error(f"Invalid package name:{pkg_name}")

def execute(args):
    install.install_packages(args.host_name[0], args.packages)
