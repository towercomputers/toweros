from towerlib import sshconf

def add_args(argparser):
    argparser.add_parser('synctime')

# pylint: disable=unused-argument
def check_args(args, parser_error):
    pass

def execute(args):
    sshconf.sync_time()
