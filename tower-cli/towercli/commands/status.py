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
    status_parser.add_argument(
        '--json',
        help="""Json output. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )

def check_args(args, parser_error):
    config = sshconf.get(args.host[0])
    if config is None:
        parser_error("Unknown host.")

def execute(args):
    if args.json:
        print(json.dumps(sshconf.status(args.host), indent=4))
    else:
        sshconf.display_status(args.host)
