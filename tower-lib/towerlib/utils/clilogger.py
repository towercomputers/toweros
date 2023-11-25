import logging

from rich import print as rprint
from rich.text import Text

def initialize(verbose=False, quiet=False):
    level = logging.INFO
    if verbose != quiet:
        level = logging.DEBUG if verbose else logging.ERROR
    logger = logging.getLogger('tower')
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    return logger

def print_error(message):
    rprint(Text(f"TOWER ERROR: {message}", style="bold red"))
