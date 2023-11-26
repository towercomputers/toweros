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
        '--nx-limit',
        help="""Specify a bitrate limit allowed for this session. (Default: 0)""",
        type=int,
        required=False,
        default=0
    )
    run_parser.add_argument(
        '--nx-images',
        help="""Size of the persistent image cache. (Default: 512M)""",
        required=False,
        default="512M"
    )
    run_parser.add_argument(
        '--nx-cache',
        help="""Size of the in-memory X message cache. Setting the value to 0 will disable the memory cache as well as the NX differential compression. (Default: 1G)""",
        required=False,
        default="1G"
    )
    run_parser.add_argument(
        '--nx-stream',
        help="""Enable or disable the ZLIB stream compression. The value must be between 0 and 9.""",
        choices=range(10),
        type=int,
        required=False
    )
    run_parser.add_argument(
        '--nx-data',
        help="""Enable or disable the ZLIB stream compression. The value must be between 0 and 9.""",
        choices=range(10),
        type=int,
        required=False
    )
    run_parser.add_argument(
        '--nx-delta',
        help="""Enable X differential compression.""",
        choices=['0', '1'],
        required=False
    )

def check_nx_args(args, parser_error):
    links = ['modem', 'isdn', 'adsl', 'wan', 'lan', 'local']
    regex = r'^[0-9]+[kmgKMG]{1}$'
    if not re.match(regex, args.nx_link) and args.nx_link not in links:
        parser_error("Invalid link name")
    if not re.match(regex, args.nx_images) and not args.nx_images.isdigit():
        parser_error("Invalid images size")
    if not re.match(regex, args.nx_cache) and not args.nx_cache.isdigit():
        parser_error("Invalid cache size")

def check_args(args, parser_error):
    config = sshconf.get(args.host_name[0])
    if config is None:
        parser_error("Unknown host.")
    check_nx_args(args, parser_error)

def execute(args):
    if os.getenv('DISPLAY'):
        nxagent_args = {
            "link": args.nx_link,
            "limit": args.nx_limit,
            "images": args.nx_images,
            "cache": args.nx_cache,
        }
        if args.nx_stream:
            nxagent_args["stream"] = args.nx_stream
        if args.nx_data:
            nxagent_args["data"] = args.nx_data
        if args.nx_delta:
            nxagent_args["delta"] = args.nx_delta
        gui.run(args.host_name[0], nxagent_args, *args.run_command)
    else:
        raise TowerException("`tower run` requires a running desktop environment. Use `startx` to start X.Org.")
