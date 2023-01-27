import glob
import os
from lib.configs import default_config_dir

def check_args(args, parser_error):
    if args.name:
        config_dir = args.config_dir or default_config_dir()
        config_file = os.path.join(config_dir, f'{args.name}.ini')
        if not os.path.exists(config_file):
            parser_error("Unknown computer name.")

def execute(args):
    config_dir = args.config_dir or default_config_dir()
    files = glob.glob('*.ini', root_dir=config_dir)

    applications_by_computer = {}
    for config_file in files:
        parts = config_file.split(".")
        computer = parts[0]
        if computer not in applications_by_computer:
            applications_by_computer[computer] = []
        if len(parts) == 3:
            applications_by_computer[computer].append(parts[1])
    
    if args.name:
        print(applications_by_computer[args.name])
    else:
        print(applications_by_computer)