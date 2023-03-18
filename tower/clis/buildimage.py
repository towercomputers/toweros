import argparse
import os

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
        help="""Skip `nx` compilation and use packages in provided folder path.""",
        required=False
    )
    parser.add_argument(
        '--computer-image-path',
        help="""Skip computer image building and use provided image path.""",
        required=False
    )
    parser.add_argument(
        '--tower-tools-wheel-path',
        help="""Tower tools wheel package path.""",
        required=False
    )

    parser.add_argument(
        'image_name', 
        help="""`thinclient` or `computer` (Required).""",
        choices=['thinclient', 'computer']
    )

    args = parser.parse_args()
    if args.computer_image_path and args.computer_image_path.split(".").pop() != "xz":
        parser.error("Invalid image path. Must be an xz archive.")
    if args.nx_path and not os.path.isdir(args.nx_path):
        parser.error("Invalid nx path. Must be a folder containing zst files.")
    return args


def main():
    args = parse_arguments()
    clilogger.initialize(args.verbose, args.quiet)
    if args.image_name == 'computer':
        pigen.build_image()
    elif args.image_name == 'thinclient':
        archiso.build_image(args.nx_path, args.computer_image_path, args.tower_tools_wheel_path)


