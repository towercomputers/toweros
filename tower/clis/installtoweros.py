import os
import sys

from sh import Command

from tower.utils import askconfiguration

INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'toweros-thinclient')

def main():
    config = askconfiguration.ask_config()
    installer_path = os.path.join(INSTALLER_DIR, 'install_thinclient.sh')
    Command(installer_path)(
        config["ROOT_PASSWORD"],
        config["USERNAME"],
        config["PASSWORD"],
        config["LANG"],
        config["TIMEZONE"],
        config["KEYBOARD_LAYOUT"],
        config["KEYBOARD_VARIANT"],
        config["TARGET_DRIVE"],
        _out=sys.stdout, 
        _err=sys.stderr
    )
