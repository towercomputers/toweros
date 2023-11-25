import logging

from towerlib import provision, sshconf

logger = logging.getLogger('tower')

def add_args(argparser):
    connect_parser = argparser.add_parser(
        'wlan-connect',
        help="""Command used to update WiFi credentials on the router."""
    )

    connect_parser.add_argument(
        '--ssid',
        help="""WiFi SSID""",
        required=True,
    )
    connect_parser.add_argument(
        '--password',
        help="""WiFi password""",
        required=True,
    )

def check_args(args, parser_error):
    if not sshconf.exists(sshconf.ROUTER_HOSTNAME):
        parser_error(message=f"`{sshconf.ROUTER_HOSTNAME}` host not found. Please provision it first.")

def execute(args):
    provision.wlan_connect(args.ssid, args.password)
