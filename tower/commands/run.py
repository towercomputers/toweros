import os
import sys

import x2go
import gevent

from tower import computers, defaults


def check_args(args, parser_error):
    config = computers.get_config(args.computer_name[0])
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
    # TODO: x2go should support ~/.ssh/config
    computer_config = computers.get_config(args.computer_name[0])

    run_application(
        computer_config['hostname'], 
        defaults.DEFAULT_SSH_PORT, 
        defaults.DEFAULT_SSH_USER, 
        computer_config['identityfile'], 
        " ".join(args.run_command)
    )