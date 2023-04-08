import re

from tower import sshconf

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
    install_parser.add_argument(
        '--online-host', 
        help="""Host name used to download the file (Default: same as `name`)""",
        required=False,
    )

def check_args(args, parser_error):
    name = args.host_name[0]
    config = sshconf.get(name)
    if config is None:
        parser_error("Unkown host name.")
    elif not sshconf.is_online(name) and args.online_host is None:
        parser_error(f"{name} is not online. Please use the flag `--online-host`.")
    
    for pkg_name in args.packages:
        if re.match(r'^[a-z0-9]{1}[a-z0-9\-\+\.]+$', pkg_name) is None:
            parser_error(f"Invalid package name:{pkg_name}")

    if args.online_host:
        config = sshconf.get(args.online_host)
        if config is None:
            parser_error("Unkown host name for online host.")
        elif not sshconf.is_online(args.online_host):
            parser_error(f"{args.online_host} is not online.")

def execute(args):
    pass
    #install(args.host_name[0], args.packages, args.online_host)
