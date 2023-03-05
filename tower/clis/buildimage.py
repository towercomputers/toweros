import argparse

from tower.raspberrypios import pigen
from tower.archlinux import archiso
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
    parser.add_argument(
        '--nx-path',
        help="""Skip `nx` compilation and use packages in provided path.""",
        required=False
    )
    parser.add_argument(
        'image_name', 
        help="""`thinclient` or `computer` (Required).""",
        choices=['thinclient', 'computer']
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    clilogger.initialize(args.verbose, args.quiet)
    if args.image_name == 'computer':
        pigen.build_image()
    elif args.image_name == 'thinclient':
        archiso.build_image(args.nx_path)


