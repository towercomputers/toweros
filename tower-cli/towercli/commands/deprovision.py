from towerlib import provision, sshconf

def add_args(argparser):
    help_message = "Deprovision a host."
    parser = argparser.add_parser(
        'deprovision',
        help=help_message, description=help_message
    )
    parser.add_argument(
        'name',
        nargs=1,
        help="""Host's name to delete (Required)"""
    )
    # pylint: disable=duplicate-code
    parser.add_argument(
        '--no-confirm',
        help="""Don't ask for confirmation. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )

def check_args(args, parser_error):
    if not sshconf.exists(args.name[0]):
        parser_error("Host not found in TowerOS configuration file.")

def execute(args):
    provision.deprovision(args.name[0], no_confirm=args.no_confirm)
