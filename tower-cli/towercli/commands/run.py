import os
import logging
import re

from towerlib import sshconf
from towerlib import gui
from towerlib.utils.exceptions import TowerException

logger = logging.getLogger('tower')

def add_args(argparser):
    run_parser = argparser.add_parser(
        'run',
        help="Run an application on the specified host, with the GUI on the thin client."
    )

    run_parser.add_argument(
        'host_name',
        help="""Host's name. This name must match the `name` used with the `provision` command. (Required)""",
        nargs=1
    )
    run_parser.add_argument(
        'run_command',
        help="""Command to execute on the host with NX protocol. (Required)""",
        nargs='+'
    )
    run_parser.add_argument(
        '--nx-link',
        help="""The value can be either 'modem', 'isdn', 'adsl', 'wan', 'lan', 'local' or a bandwidth specification, like for example '56k', '1m', '100m'""",
        required=False,
        default="adsl"
    )
    run_parser.add_argument(
        '--nx-stream',
        help="""Enable or disable the ZLIB stream compression. The value must be between 0 and 9.""",
        choices=range(10),
        type=int,
        required=False
    )
    run_parser.add_argument(
        '--nx-limit',
        help="""Specify a bitrate limit allowed for this session. (Default: 0)""",
        type=int,
        required=False,
        default=0
    )

def check_link_arg(args, parser_error):
    if args.nx_link in ['modem', 'isdn', 'adsl', 'wan', 'lan', 'local']:
        return
    if not re.match(r'^[0-9]+[kmg]{1}$', args.nx_link):
        parser_error("Invalid link name")

def check_args(args, parser_error):
    config = sshconf.get(args.host_name[0])
    if config is None:
        parser_error("Unknown host.")
    check_link_arg(args, parser_error)

def execute(args):
    if os.getenv('DISPLAY'):
        nxagent_args = {
            "link": args.nx_link,
            "limit": args.nx_limit,
        }
        if args.nx_stream:
            nxagent_args["stream"] = args.nx_stream
        gui.run(args.host_name[0], nxagent_args, *args.run_command)
    else:
        raise TowerException("`tower run` requires a running desktop environment. Use `startx` to start X.Org.")
