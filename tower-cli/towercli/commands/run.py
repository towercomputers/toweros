import os
import logging
import re

from towerlib import sshconf
from towerlib import gui, vnc
from towerlib.utils.exceptions import TowerException

logger = logging.getLogger('tower')


def add_args(argparser):
    help_message = "Run an application on the specified host, with the GUI on the thin client."
    run_parser = argparser.add_parser(
        'run',
        help=help_message, description=help_message
    )
    run_parser.add_argument(
        'host',
        help="""Host's name. This name must match the `name` used with the `provision` command. (Required)""",
        nargs=1
    )
    run_parser.add_argument(
        'run_command',
        help="""Command to execute on the host with NX protocol. (Required)""",
        nargs='+'
    )
    run_parser.add_argument(
        '--uncolored',
        help="""Don't use host color for window headerbar. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    run_parser.add_argument(
        '--vnc-speeds',
        help="""The triple rd,bw,lat corresponds to video h/w read rate in MB/sec, network bandwidth to clients in KB/sec, and network latency to clients in milliseconds, respectively. If a value is left blank, e.g. "-speeds ,100,15", then the internal scheme is used to estimate the empty value(s).""",
        required=False
    )
    run_parser.add_argument(
        '--vnc-grab',
        help="""Grab host keyboard and mouse events (run x11vnc with -grabkbd and -grabptr flags). (Default: False except for Firefox)""",
        required=False,
        action='store_true',
        default=False
    )


def check_args(args, parser_error):
    config = sshconf.get(args.host[0])
    if config is None:
        parser_error("Unknown host.")


def execute(args):
    if os.getenv('DISPLAY'):
        vnc.run(args.host[0], ' '.join(args.run_command), args)
    else:
        raise TowerException("`tower run` requires a running desktop environment. Use `startw` to start Labwc.")
