import argparse
import tower
from tower.commands import provision, install, run, list

def parse_arguments():
    parser = argparse.ArgumentParser(description="""
        Tower Computing command line.
        Provision a computer with the `provision` command then install on it an application with `install` and finally run the applications with the `run` command. 
        Use `./tower {provision|install|run} --help` to get options list for each command.
    """)

    subparser = parser.add_subparsers(dest='command', required=True)

    ##########################
    #  `provision` command   #
    ##########################

    provision_parser = subparser.add_parser(
        'provision',
        help="""Command used to prepare the bootable SD Card needed to provision a computer."""
    )
    provision_parser.add_argument(
        'name', 
        nargs=1,
        help="""Computer's name. This name is used to install and run an application (Required)."""
    )
    provision_parser.add_argument(
        '-sd', '--sd-card', 
        help="""SD Card path.""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--public-key-path', 
        help="""Public key path used to access the application computer (Default: automatically generated and stored in the SD card and the local ~/.ssh/ folder).""",
        required=False
    )
    provision_parser.add_argument(
        '--private-key-path', 
        help="""Private key path used to access the application computer (Default: automatically generated and stored in the local ~/.ssh/ folder).""",
        required=False
    )
    provision_parser.add_argument(
        '--keymap', 
        help="""Keyboard layout code (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--timezone', 
        help="""Timezone of the computer (Default: same as the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--online', 
        help="""Set wifi connection (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    provision_parser.add_argument(
        '--wlan-ssid', 
        help="""Wifi SSID (Default: same as the connection currently used by the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--wlan-password', 
        help="""Wifi password (Default: same as the connection currently used by the thin client)""",
        required=False,
        default=""
    )
    provision_parser.add_argument(
        '--wlan-country', 
        help="""Wifi country (Default: same as the connection currently used by the thin client)""",
        required=False,
        default=""
    )


    ##########################
    #  `install` command     #
    ##########################

    install_parser = subparser.add_parser(
        'install',
        help="""Command used to install an application in a computer prepared with the `provision` command."""
    )

    # TODO: support multiple install
    install_parser.add_argument(
        'computer_name', 
        help="""Computer name where to install the package (Required).""",
        nargs=1
    )
    install_parser.add_argument(
        'packages', 
        help="""Package(s) to install (Required).""",
        nargs='+'
    )
    install_parser.add_argument(
        '--online-host', 
        help="""Computer name used to download the file (Default: same as `name`)""",
        required=False,
    )


    ##########################
    #  `run` command         #
    ##########################

    run_parser = subparser.add_parser(
        'run',
        help="Command used to run an application prepared with `install` command."
    )

    run_parser.add_argument(
        'computer_name', 
        help="""Computer's name. This name must match with the `name` used with the `provision` command (Required).""",
        nargs=1
    )
    run_parser.add_argument(
        'run_command', 
        help="""Command to execute with X2GO (Required).""",
        nargs='+'
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

