import os
from lib.configs import default_config_dir, get_tower_config

def check_args(args, parser_error):
    print(args)

def execute(args):
    tower_config = get_tower_config(args.config_dir)
    print(dict(tower_config))