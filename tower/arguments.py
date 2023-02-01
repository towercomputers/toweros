import argparse
import tower
from tower.commands import provision, install, run, list

def parse_arguments():
    parser = argparse.ArgumentParser(description="""
        Tower Computing command line.
        Provision a computer with the `provision` command then install on it an application with `install` and finally run the applications with the `run` command. 
        Use `./tower {provision|install|run} --help` to get options list for each command.
    """)

    parser.add_argument(
        '--config-dir', 
        help="""Directory where config files are placed (Default: ~/.config/tower/).""",
        required=False
    )

    subparser = parser.add_subparsers(dest='command', required=True)

    ##########################
    #  `provision` command   #
    ##########################

    provision_parser = subparser.add_parser(
        'provision',
        help="""Command used to prepare the bootable SD Card needed to provision a computer."""
    )

    provision_parser.add_argument(
        '-n', '--name', 
        help="""Computer's name. This name is used to install and run an application (Required).""",
        required=True
    )
    provision_parser.add_argument(
        '-sd', '--sd-card', 
        help="""SD Card path.""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--public-key', 
        help="""Public key path used to access the application computer (Default: automatically generated and stored in the SD card and the local ~/.ssh/ folder).""",
        required=False
    )
    provision_parser.add_argument(
        '--private-key', 
        help="""Private key path used to access the application computer (Default: automatically generated and stored in the local ~/.ssh/ folder).""",
        required=False
    )

    ##########################
    #  `install` command     #
    ##########################

    install_parser = subparser.add_parser(
        'install',
        help="""Command used to install an application in a computer prepared with the `provision` command."""
    )

    install_parser.add_argument(
        '-n', '--name', 
        help="""Computer's name where to install the application. A config file MUST exists for this name (Required).""",
        required=True
    )
    install_parser.add_argument(
        '-p', '--path', 
        help="""Application's binary path in the application computer (Required).""",
        required=True
    )
    install_parser.add_argument(
        '-a', '--alias',
        help="""Name used to run the application (Required).""",
        required=True
    )
    install_parser.add_argument(
        '--apt-packages', 
        help="""Comma separated list of apt packages to install in th SD Card (Default: assume the application is already installed).""",
        required=False
    )
    install_parser.add_argument(
        '--local-apt-packages', 
        help="""Comma separated list of apt packages local file pathes to install in th SD Card. (Default: assume the application is already installed)""",
        required=False
    )

    ##########################
    #  `run` command         #
    ##########################

    run_parser = subparser.add_parser(
        'run',
        help="Command used to run an application prepared with `install` command."
    )

    run_parser.add_argument(
        '-n', '--name', 
        help="""Computer's name. This name must match with the `name` used with the `provision` command (Required).""",
        required=True
    )
    run_parser.add_argument(
        '-a', '--alias', 
        help="""Application's alias. This name must match with the `alias` used with the `install` command (Required).""",
        required=True
    )

    ##########################
    #  `list` command        #
    ##########################

    list_parser = subparser.add_parser(
        'list',
        help="List all the computers and applications."
    )
    list_parser.add_argument(
        '-n', '--name', 
        help="""List only the applications installed in the given computer (Default: none).""",
        required=False
    )

    args = parser.parse_args()
    getattr(tower.commands, args.command).check_args(args, parser.error)

    return args

