import logging
import json

from tower import computers

logger = logging.getLogger('tower')

def check_args(args, parser_error):
    pass

def execute(args):
    print(json.dumps(computers.status(args.name), indent=4))