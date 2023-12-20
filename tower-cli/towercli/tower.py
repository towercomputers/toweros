import argparse
import sys

from towerlib import utils
from towerlib.utils.exceptions import TowerException

import towercli
from towercli.commands import provision, install, run, status, wlanconnect, upgrade, version, mdhelp, synctime

def towercli_parser():
    parser = argparse.ArgumentParser(
        description="TowerOS command-line interface for provisioning hosts, install APK packages on it and run applications with NX protocol.",
        prog="tower"
    )
    parser.add_argument(
        '--quiet',
        help="""Set log level to ERROR.""",
        required=False,
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--verbose',
        help="""Set log level to DEBUG.""",
        required=False,
        action='store_true',
        default=False
    )
    subparser = parser.add_subparsers(
        dest='command',
        required=True,
        help="Use `tower {provision|upgrade|install|run|status|wlan-connect|version} --help` to get the options list for each command.",
        metavar="{provision,upgrade,install,run,status,wlan-connect,version}}"
    )
    provision.add_args(subparser)
    upgrade.add_args(subparser)
    install.add_args(subparser)
    run.add_args(subparser)
    status.add_args(subparser)
    wlanconnect.add_args(subparser)
    version.add_args(subparser)
    mdhelp.add_args(subparser) # hidden command
    synctime.add_args(subparser) # hidden command
    utils.mdhelp.insert_autocompletion_command(parser) # hidden command
    return parser

def get_module(args):
    module_name = args.command.replace("-", "")
    return getattr(towercli.commands, module_name)

def parse_arguments():
    parser = towercli_parser()
    args = parser.parse_args()
    get_module(args).check_args(args, parser.error)
    return args

def main():
    try:
        args = parse_arguments()
        utils.clilogger.initialize(args.verbose, args.quiet)
        if args.command == 'mdhelp':
            mdhelp.execute(towercli_parser())
        else:
            get_module(args).execute(args)
    except TowerException as exc:
        utils.clilogger.print_error(str(exc))
        sys.exit()
