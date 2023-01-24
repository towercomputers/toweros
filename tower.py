#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description="""Tower Computing command line to prepare SD cards and run applications. 
This command line is used as backend for the TS GUI.""")

subparser = parser.add_subparsers(dest='command')

createapp = subparser.add_parser(
    'createapp',
    help="""Command used to prepare a bootable SD Card. 
A profile file containing all the information needed to execute the `runapp` command will be created in the local config folder ~/.config/ts/."""
)
runapp = subparser.add_parser(
    'runapp',
    help="Command used to run an application prepared with `createapp` command."
)

createapp.add_argument(
    '-n', '--name', 
    help="""Application's name. This name is used to run the application.""",
    required=True
)
createapp.add_argument(
    '-d', '--host', 
    help="""IP or domain name of the application computer.""",
    required=True
)
createapp.add_argument(
    '-sd', '--sd-card', 
    help="""SD Card path.""",
    required=True
)
createapp.add_argument(
    '-p', '--path', 
    help="""Application's binary path in the application computer.""",
    required=True
)
createapp.add_argument(
    '-m', '--netmask', 
    help="""Netmask of the application computer.""",
    required=False
)
createapp.add_argument(
    '-puk', '--public-key', 
    help="""Public key path used to access the application computer. 
If not provided, a key will be automatically generated and stored in the SD card and the local ~/.ssh/ folder.""",
    required=False
)
createapp.add_argument(
    '-prk', '--private-key', 
    help="""Private key path used to access the application computer. 
If not provided, a key will be automatically generated and stored in the local ~/.ssh/ folder.""",
    required=False
)
createapp.add_argument(
    '-pass', '--passphrase', 
    help="""Passphrase used to protect the private key.""",
    required=True
)
createapp.add_argument(
    '-c', '--config-dir', 
    help="""Directory where the config file for this appication will be placed (default  ~/.config/ts/).""",
    required=False
)
createapp.add_argument(
    '-ap', '--apt-packages', 
    help="""Comma separated list of apt packages to install in th SD Card.""",
    required=False
)
createapp.add_argument(
    '-lap', '--local-apt-packages', 
    help="""Comma separated list of apt packages local file pathes to install in th SD Card.""",
    required=False
)


runapp.add_argument(
    '-n', '--name', 
    help="""Application's name. This name must match with the `name` used with the `createapp` command.""",
    required=True
)
runapp.add_argument(
    '-pass', '--passphrase', 
    help="""Passphrase used to protect the private key.""",
    required=True
)
runapp.add_argument(
    '-d', '--host', 
    help="""IP or domain name of the application computer.""",
    required=False
)
runapp.add_argument(
    '-p', '--path', 
    help="""Application's binary path in the application computer.""",
    required=False
)
runapp.add_argument(
    '-m', '--netmask', 
    help="""Netmask of the application computer.""",
    required=False
)
runapp.add_argument(
    '-prk', '--private-key', 
    help="""Private key path used to access the application computer. If not provided, the key ~/.ssh/{name}.key will be used.""",
    required=False
)
runapp.add_argument(
    '-c', '--config-dir', 
    help="""Directory where the config file for this appication is placed (default  ~/.config/ts/).""",
    required=False
)

args = parser.parse_args()

print(args)
#parser.print_help()
