import os
import re
from lib.configs import default_config_dir, create_application_config

def check_args(args, parser_error):
    if re.match(r'/^(?![0-9]{1,15}$)[a-zA-Z0-9-]{1,15}$/', args.alias):
        parser_error(message="Application alias invalid. Must be between one and 15 alphanumeric chars.")

    config_dir = args.config_dir or default_config_dir()
    config_file = os.path.join(config_dir, f'{args.name}.ini')
    if not os.path.exists(config_file):
        parser_error("Unknown computer name.")

def execute(args):
    config = create_application_config(args)
    print(f'{config}')