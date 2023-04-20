import os
import sys
import logging
import time

from tower import sshconf
from tower import gui

logger = logging.getLogger('tower')

def add_args(argparser):
    run_parser = argparser.add_parser(
        'run',
        help="Command used to run an application prepared with `install` command."
    )

    run_parser.add_argument(
        'host_name', 
        help="""Host's name. This name must match with the `name` used with the `provision` command (Required).""",
        nargs=1
    )
    run_parser.add_argument(
        'run_command', 
        help="""Command to execute with X2GO (Required).""",
        nargs='+'
    )    

def check_args(args, parser_error):
    config = sshconf.get(args.host_name[0])
    if config is None:
        parser_error("Unkown host name.")

def execute(args):
    if os.getenv('DISPLAY'):
        gui.run(args.host_name[0], *args.run_command)
    else:
        # TODO: find a more elegant way or remove ?
        clean_startup = "sed -i \'/\\[startup\\]/d\' ~/.fluxbox/apps"
        run_command = " ".join(sys.argv)
        startup_line = f'[startup] {{{clean_startup} && {run_command}}}'
        add_startup = f'echo "{startup_line}" >> ~/.fluxbox/apps'
        cmd = f"{add_startup} && startx"
        os.system(cmd)
        #logger.error("ERROR: `tower run` requires a running desktop environment. Use `startx` to run the desktop then right click to see all installed application.")
    
