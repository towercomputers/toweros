import os
import sys

import x2go
import gevent

from tower import computers

from tower.configs import (
    default_config_dir, 
    get_tower_config
)

def check_args(args, parser_error):
    config = computers.get_computer_config(args.config_dir, args.computer_name[0])
    if config is None:
        parser_error("Unkown computer name.")

def run_application(host, port, username, key_filename, command):
    cli = x2go.X2GoClient(use_cache=False, loglevel=x2go.log.loglevel_DEBUG)
    s_uuid = cli.register_session(
        host, 
        port=port,
        username=username,
        cmd=command,
        look_for_keys=False,
        key_filename=key_filename
    )
    cli.connect_session(s_uuid)
    cli.clean_sessions(s_uuid)
    cli.start_session(s_uuid)

    try:
        while cli.session_ok(s_uuid):
            gevent.sleep(2)
    except KeyboardInterrupt:
        pass

    cli.suspend_session(s_uuid)


def execute(args):
    tower_config = get_tower_config(args.config_dir)
    computer_config = computers.get_computer_config(args.config_dir, args.computer_name[0])

    # TODO: x2go should support ~/.ssh/config
    ip = computer_config.get('ip')
    if not ip:
        sys.exit('Unkown IP. Please run `tower config refresh`') # TODO: hum.. blah..

    run_application(
        ip, 
        tower_config.get('default-ssh-port'), 
        tower_config.get('default-ssh-user'), 
        computer_config.get('private-key-path'), 
        " ".join(args.run_command)
    )