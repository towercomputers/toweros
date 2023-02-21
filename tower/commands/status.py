import json

from tower import computers

def add_args(argparser):
    status_parser = argparser.add_parser(
        'status',
        help="Get status of all the computers."
    )

def check_args(args, parser_error):
    pass

def execute(args):
    print(json.dumps(computers.status(), indent=4))
