import os
import sys

from sh import Command

from tower.utils import askconfiguration

INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'toweros-thinclient')

def main():
    config = askconfiguration.ask_config()
    print(config)
    installer_path = os.path.join(INSTALLER_DIR, 'alpine_install.sh')
    Command(installer_path)(_out=sys.stdout, _err=sys.stderr)
