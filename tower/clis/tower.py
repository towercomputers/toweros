import argparse

import tower
from tower.clis.commands import provision, install, run, status, wlanconnect
from tower import utils

def parse_arguments():
    parser = argparse.ArgumentParser(description="""
        Tower Computing command line to provision a host, install apt packages on it and run applications with x2go.
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
    subparser = parser.add_subparsers(dest='command', required=True, help="Use `tower {provision|install|run|status|wlan-connect} --help` to get options list for each command.")
    tower.clis.commands.provision.add_args(subparser)
    tower.clis.commands.install.add_args(subparser)
    tower.clis.commands.run.add_args(subparser)
    tower.clis.commands.status.add_args(subparser)
    tower.clis.commands.wlanconnect.add_args(subparser)
    args = parser.parse_args()
    getattr(tower.clis.commands, args.command.replace("-", "")).check_args(args, parser.error)
    return args

def main():
    args = parse_arguments()
    utils.clilogger.initialize(args.verbose, args.quiet)
    getattr(tower.clis.commands, args.command.replace("-", "")).execute(args)
