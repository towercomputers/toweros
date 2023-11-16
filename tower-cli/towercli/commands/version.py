import json

from towerlib import sshconf

def add_args(argparser):
    status_parser = argparser.add_parser(
        'version',
        help="Get Thin Client and Hosts versions."
    )

def check_args(args, parser_error):
    pass

def execute(args):
    print(json.dumps(sshconf.get_version(), indent=4))
