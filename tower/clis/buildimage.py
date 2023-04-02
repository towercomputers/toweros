import argparse
import os

from tower.archlinux import archiso, pigen
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
    subparser = parser.add_subparsers(
        dest='image_name', 
        required=True, 
        help="Use `build-tower-image {thinclient|host} --help` to get options list for each image."
    )
    thinclient_parser = subparser.add_parser(
        'thinclient',
        help="""Command used to generate thinclient image"""
    )
    thinclient_parser.add_argument(
        '--nx-path',
        help="""Skip `nx` compilation and use packages in provided folder path.""",
        required=False
    )
    thinclient_parser.add_argument(
        '--host-image-path',
        help="""Skip host image building and use provided image path.""",
        required=False
    )
    thinclient_parser.add_argument(
        '--tower-tools-wheel-path',
        help="""Tower tools wheel package path.""",
        required=False
    )
    host_parser = subparser.add_parser(
        'host',
        help="""Command used to generate host image."""
    )
    host_parser.add_argument(
        '--nx-tar-path',
        help="""`nx` compiled package path.""",
        required=True
    )
    host_parser.add_argument(
        '--archlinux-tar-path',
        help="""Arch Linux Arm packages.""",
        required=True
    )

    args = parser.parse_args()
    if args.image_name == 'thinclient':
        if args.host_image_path:
            if not os.path.exists(args.host_image_path):
                parser.error("Invalid host image path. File not found.")
            if args.host_image_path.split(".").pop() != "xz":
                parser.error("Invalid image path. Must be an xz archive.")
        if args.nx_path and not os.path.isdir(args.nx_path):
            parser.error("Invalid nx path. Must be a folder containing zst files.")
    if args.image_name == 'host':
        if args.nx_tar_path:
            if not os.path.exists(args.nx_tar_path):
                parser.error("Invalid nx tar path. File not found.")
            if args.nx_tar_path.split(".")[-2:] != ["tar", "gz"]:
                parser.error("Invalid nx tar path. Must be an tar.gz archive.")
        if args.archlinux_tar_path:
            if not os.path.exists(args.archlinux_tar_path):
                parser.error("Invalid Arch Linux tar path. File not found.")
            if args.archlinux_tar_path.split(".")[-2:] != ["tar", "gz"]:
                parser.error("Invalid Arch Linux tar path. Must be an tar.gz archive.")
        
    return args

def main():
    args = parse_arguments()
    clilogger.initialize(args.verbose, args.quiet)
    if args.image_name == 'host':
        pigen.build_image(args.archlinux_tar_path, args.nx_tar_path)
    elif args.image_name == 'thinclient':
        archiso.build_image(args.nx_path, args.host_image_path, args.tower_tools_wheel_path)


