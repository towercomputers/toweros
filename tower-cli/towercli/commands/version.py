import json

from towerlib import sshconf

def add_args(argparser):
    status_parser = argparser.add_parser(
        'version',
        help="Get the version of TowerOS installed on the thin client and hosts."
    )

def check_args(args, parser_error):
    pass

def execute(args):
    print(json.dumps(sshconf.get_version(), indent=4))
