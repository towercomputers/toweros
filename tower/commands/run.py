from tower import computers

def add_args(argparser):
    run_parser = argparser.add_parser(
        'run',
        help="Command used to run an application prepared with `install` command."
    )

    run_parser.add_argument(
        'computer_name', 
        help="""Computer's name. This name must match with the `name` used with the `provision` command (Required).""",
        nargs=1
    )
    run_parser.add_argument(
        'run_command', 
        help="""Command to execute with X2GO (Required).""",
        nargs='+'
    )    

def check_args(args, parser_error):
    config = computers.get_config(args.computer_name[0])
    if config is None:
        parser_error("Unkown computer name.")

def execute(args):
    computers.run(args.computer_name[0], " ".join(args.run_command))
