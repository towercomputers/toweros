import os

import x2go
import gevent

from lib.configs import (
    default_config_dir, 
    get_tower_config, 
    get_computer_config, 
    get_application_config
)

def check_args(args, parser_error):
    config_dir = args.config_dir or default_config_dir()

    computer_config_file = os.path.join(config_dir, f'{args.name}.ini')
    if not os.path.exists(computer_config_file):
        parser_error("Unkown computer name.")
    
    application_config_file = os.path.join(config_dir, f'{args.name}.{args.alias}.ini')
    if not os.path.exists(application_config_file):
        parser_error("Unkown application alias.")


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
    computer_config = get_computer_config(args.config_dir, args.name)
    application_config = get_application_config(args.config_dir, args.name, args.alias)

    run_application(
        computer_config.get('host'), 
        tower_config.get('default_ssh_port'), 
        tower_config.get('default_ssh_user'), 
        computer_config.get('private_key'), 
        application_config.get('path')
    )