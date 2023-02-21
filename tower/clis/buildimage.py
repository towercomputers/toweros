import argparse

from tower.raspberrypios import pigen
from tower.clis import clilogger

def parse_arguments():
    parser = argparse.ArgumentParser(description="""Generate Raspberry Pi OS image compatible with `tower`""")
    parser.add_argument(
        '-v', '--verbose',
        help="""Set log level to DEBUG.""",
        required=False,
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--quiet',
        help="""Set log level to ERROR.""",
        required=False,
        action='store_true',
        default=False
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    clilogger.initialize(args.verbose, args.quiet)
    pigen.build_image()


