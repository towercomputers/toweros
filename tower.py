#!/usr/bin/env python3

import warnings
warnings.filterwarnings("ignore") # TODO: fix x2go syntax warning in python3

import lib
from lib.arguments import parse_arguments 
from lib.commands import provision, install, run, list

args = parse_arguments()
getattr(lib.commands, args.command).execute(args)
