import argparse
import sys

from towerlib import utils
from towerlib.utils.exceptions import TowerException

import towercli
# import needed for getattr() in parse_arguments()
# pylint: disable=unused-import
from towercli.commands import provision, install, run, status, wlanconnect, upgrade, version

def towercli_parser():
    parser = argparse.ArgumentParser(description="""
        TowerOS command-line interface for provisioning hosts, install APK packages on it and run applications with NX protocol.
    """)
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
    subparser = parser.add_subparsers(dest='command', required=True, help="Use `tower {provision|install|run|status|wlan-connect} --help` to get the options list for each command.")
    towercli.commands.provision.add_args(subparser)
    towercli.commands.upgrade.add_args(subparser)
    towercli.commands.install.add_args(subparser)
    towercli.commands.run.add_args(subparser)
    towercli.commands.status.add_args(subparser)
    towercli.commands.wlanconnect.add_args(subparser)
    towercli.commands.version.add_args(subparser)
    return parser

def parse_arguments():
    parser = towercli_parser()
    args = parser.parse_args()
    getattr(towercli.commands, args.command.replace("-", "")).check_args(args, parser.error)
    return args

def main():
    try:
        args = parse_arguments()
        utils.clilogger.initialize(args.verbose, args.quiet)
        getattr(towercli.commands, args.command.replace("-", "")).execute(args)
    except TowerException as e:
        utils.clilogger.print_error(str(e))
        sys.exit()
