import json

from towerlib import sshconf

def add_args(argparser):
    help_message = "Check the status of all hosts in the Tower system."
    status_parser = argparser.add_parser(
        'status',
        help=help_message, description=help_message
    )
    status_parser.add_argument(
        '--host',
        help="""Name of the host you want to check the status. If not specified, the status of all hosts will be displayed.""",
        required=False,
        default=None
    )

# pylint: disable=unused-argument
def check_args(args, parser_error):
    pass

# pylint: disable=unused-argument
def execute(args):
    print(json.dumps(sshconf.status(args.host), indent=4))
