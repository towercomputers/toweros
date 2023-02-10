import glob
import os
from tower.configs import default_config_dir
from tower import computers

def check_args(args, parser_error):
    pass

def execute(args):
    print(computers.get_list())