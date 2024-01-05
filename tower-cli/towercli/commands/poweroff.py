from towerlib import sshconf

from towercli.commands import status as status_command

def add_args(argparser):
    help_message = "Poweroff all hosts."
    status_parser = argparser.add_parser(
        'poweroff',
        help=help_message, description=help_message
    )
    status_parser.add_argument(
        '--host',
        help="""Name of the host you want to poweroff.""",
        required=False,
        default=None
    )


def check_args(args, parser_error):
    status_command.check_args(args, parser_error)


def execute(args):
    sshconf.poweroff(args.host)
