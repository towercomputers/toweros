#!/usr/bin/env python3

import warnings
warnings.filterwarnings("ignore") # TODO: fix x2go syntax warning in python3

import tower
from tower.arguments import parse_arguments 
from tower.commands import provision, install, run, list

args = parse_arguments()
getattr(tower.commands, args.command).execute(args)