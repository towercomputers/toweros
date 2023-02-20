import argparse
import logging

from tower.raspberrypios import pigen

def main():
    parser = argparse.ArgumentParser(description="""Generate Raspberry Pi OS compatible with `tower`""")
    parser.add_argument(
        '-v', '--verbose',
        help="""Set log level to DEBUG.""",
        required=False,
        action='store_true',
        default=False
    )
    args = parser.parse_args()

    logger = logging.getLogger('tower')
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    logger.addHandler(console_handler)

    pigen.build_image()


