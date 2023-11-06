import json

from towerlib import sshconf

def add_args(argparser):
    status_parser = argparser.add_parser(
        'status',
        help="Get status of all the hosts."
    )

def check_args(args, parser_error):
    pass

def execute(args):
    print(json.dumps(sshconf.status(), indent=4))
