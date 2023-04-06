import argparse
import os

from tower import toweros, towerospi
from tower.clis import clilogger

def get_builds_dir(args):
    builds_dir = args.builds_dir
    # if not provided check if builds is in ./ or ~/.cache/tower/
    if not builds_dir:
        builds_dir = os.path.join(os.getcwd(), 'builds')
        if os.path.isdir(builds_dir):
            return builds_dir
        builds_dir = os.path.join(os.path.expanduser('~'), '.cache', 'tower', 'builds')
        if os.path.isdir(builds_dir):
            return builds_dir
    return builds_dir

def check_builds_dir(args, parser_error):
    builds_dir = get_builds_dir(args)
    if not builds_dir or not os.path.isdir(builds_dir):
        parser_error("Can't find builds dir, please use the flag --builds-dir")
    # check requirement for thinclient
    if args.image_name == 'thinclient':
        if not os.path.isfile(os.path.join(builds_dir, 'nx-x86_64.tar.gz')):
            parser_error(f"Can't find nx-x86_64.tar.gz in {builds_dir}")
    # check requirement for host
    if args.image_name == 'host':
        if not os.path.isfile(os.path.join(builds_dir, 'nx-armv7h.tar.gz')):
            parser_error(f"Can't find nx-armv7h.tar.gz in {builds_dir}")

def parse_arguments():
    parser = argparse.ArgumentParser(description="""Generate TowerOS and TowerOS PI images""")
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
        '--builds-dir',
        help="""Directory containing builds necessary to build an image.""",
        required=False,
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
    host_parser = subparser.add_parser(
        'host',
        help="""Command used to generate host image."""
    )
    args = parser.parse_args()
    check_builds_dir(args, parser.error)
    return args

def main():
    args = parse_arguments()
    clilogger.initialize(args.verbose, args.quiet)
    builds_dir = get_builds_dir(args)
    if args.image_name == 'host':
        towerospi.build_image(builds_dir)
    elif args.image_name == 'thinclient':
        toweros.build_image(builds_dir)


