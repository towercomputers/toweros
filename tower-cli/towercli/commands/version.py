import json

from towerlib import sshconf

def add_args(argparser):
    argparser.add_parser(
        'version',
        help="Get the version of TowerOS installed on the thin client and hosts."
    )

# pylint: disable=unused-argument
def check_args(args, parser_error):
    pass

# pylint: disable=unused-argument
def execute(args):
    print(json.dumps(sshconf.get_version(), indent=4))
