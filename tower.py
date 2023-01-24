#!/usr/bin/env python3

import lib
from lib.arguments import parse_arguments 
from lib.commands import provision, install, run, list

args = parse_arguments()
getattr(lib.commands, args.command).execute(args)