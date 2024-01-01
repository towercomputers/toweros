from towerlib import sshconf

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
    if not args.host:
        return
    config = sshconf.get(args.host)
    if config is None:
        parser_error("Unknown host.")


def execute(args):
    sshconf.poweroff(args.host)
