#!/usr/bin/env python3

import logging
import warnings
warnings.filterwarnings("ignore") # TODO: fix x2go syntax warning in python3

import tower
from tower.arguments import parse_arguments 
from tower.commands import provision, install, run, status


args = parse_arguments()

logger = logging.getLogger('tower')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()

if args.verbose:
    console_handler.setLevel(logging.DEBUG)
elif args.quiet:
    console_handler.setLevel(logging.ERROR)
else:
    console_handler.setLevel(logging.INFO)

logger.addHandler(console_handler)

getattr(tower.commands, args.command).execute(args)
