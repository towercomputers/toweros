from towerlib.utils.mdhelp import gen_md_help

def add_args(argparser):
    argparser.add_parser('mdhelp')

# pylint: disable=unused-argument
def check_args(args, parser_error):
    pass

# pylint: disable=unused-argument
def execute(parser):
    print(gen_md_help(parser))
