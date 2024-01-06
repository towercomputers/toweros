import logging

from towerlib import install, sshconf

logger = logging.getLogger('tower')


def add_args(argparser):
    help_message = "Open APK tunnel with offline host."
    parser = argparser.add_parser(
        'apk-tunnel',
        help=help_message, description=help_message
    )
    parser.add_argument(
        'host',
        help="""Host to install the package on (Required)""",
        nargs=1
    )


def check_args(args, parser_error):
    config = sshconf.get(args.host[0])
    if config is None:
        parser_error("Unknown host.")


def execute(args):
    install.open_apk_tunnel(args.host[0])
