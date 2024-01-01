#!/bin/bash
#
# The purpose of this script is to finish the installation for a development environment. 
# It performs the following actions:
#       - connects to the internet
#       - configure git and download toweros sources from Github
#       - possibly opens an ssh access

# This script must be placed on a USB stick with a `devenv` file containing the following variables:
#
# GIT_NAME="Ouziel Slama""
# GIT_EMAIL="ouziel@gmail.com"
# GIT_KEY_PATH="id_ed25519"
# AUTHORIZED_KEY="ssh-ed25519 AAAAC3NzacmuS1NTE5AAAAIJMdPXjBDbI7C1lZDI1fV4ieSkT9GJZghyXtoiI6qLils2 air"
#
# After provisioning the `router`
#
# $ sudo mount --mkdir /dev/sdb1 SD
# $ ls SD/
# install-dev-usb.sh id_ed25519
# $ sh SD/install-dev-usb.sh
#

set -e
set -x

SCRIPTS_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

# load variables
source $SCRIPTS_DIR/devenv

sh /var/towercomputers/scripts/dev/connect-wifi.sh
sh /var/towercomputers/scripts/dev/configure-git.sh "$GIT_NAME" "$GIT_EMAIL" "$GIT_KEY_PATH"
if [ ! -z "$AUTHORIZED_KEY" ]; then
    sh /var/towercomputers/scripts/dev/open-ssh.sh "$AUTHORIZED_KEY"
fi
