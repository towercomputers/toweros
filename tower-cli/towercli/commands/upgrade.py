import logging
import sys

from towercli.commands import provision as provision_command

from towerlib import provision, sshconf

logger = logging.getLogger('tower')

def add_args(argparser):
    provision_command.add_args(argparser, upgrade=True)

def check_args(args, parser_error):
    for name in args.hosts or []:
        if not sshconf.exists(name):
            parser_error(f"Host `{name}` not found in TowerOS configuration file.")
    provision_command.check_common_args(args, parser_error)

def execute(args):
    try:
        if args.hosts is None:
            provision.upgrade_thinclient(args)
        else:
            hosts = args.hosts if len(args.hosts) > 0 else list(sshconf.hosts())
            provision.upgrade_hosts(hosts, args)
    except provision.MissingEnvironmentValue as exc:
        sys.exit(str(exc))
