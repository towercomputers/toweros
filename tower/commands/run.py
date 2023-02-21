from tower import computers

def check_args(args, parser_error):
    config = computers.get_config(args.computer_name[0])
    if config is None:
        parser_error("Unkown computer name.")

def execute(args):
    computers.run(args.computer_name[0], " ".join(args.run_command))
