import json

from tower import computers

def check_args(args, parser_error):
    pass

def execute(args):
    print(json.dumps(computers.status(), indent=4))
