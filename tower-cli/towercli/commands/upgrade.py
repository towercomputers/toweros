import logging
import sys

from towercli.commands import provision as provision_command

from towerlib import provision, sshconf

logger = logging.getLogger('tower')

def add_args(argparser):
    provision_command.add_args(argparser, upgrade=True)

def check_args(args, parser_error):
    if not sshconf.exists(args.name[0]):
        parser_error("Host not found in TowerOS configuration file.")
    provision_command.check_common_args(args, parser_error)

def execute(args):
    try:
        provision.upgrade(args.name[0], args)
    except provision.MissingEnvironmentValue as exc:
        sys.exit(str(exc))
