import logging

from towerlib import provision, sshconf, config

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

# pylint: disable=unused-argument
def check_args(args, parser_error):
    if not sshconf.exists(config.ROUTER_HOSTNAME):
        parser_error(message=f"`{config.ROUTER_HOSTNAME}` host not found. Please provision it first.")

def execute(args):
    provision.wlan_connect(args.ssid, args.password)
