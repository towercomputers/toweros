import os
import logging

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

def check_args(args, parser_error):
    config = sshconf.get(args.host_name[0])
    if config is None:
        parser_error("Unknown host.")

def execute(args):
    if os.getenv('DISPLAY'):
        gui.run(args.host_name[0], *args.run_command)
    else:
        raise TowerException("`tower run` requires a running desktop environment. Use `startx` to start X.Org.")
