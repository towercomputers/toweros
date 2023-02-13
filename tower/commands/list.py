import logging

from tower import computers

logger = logging.getLogger('tower')

def check_args(args, parser_error):
    pass

def execute(args):
    print(computers.get_list())