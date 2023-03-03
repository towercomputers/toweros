#!/bin/bash

set -e
set -x

echo 'TARGET_DRIVE="/dev/sda"' > tower.env
echo 'ROOT_PASSWORD="tower"' >> tower.env
echo 'USERNAME="tower"' >> tower.env
echo 'PASSWORD="tower"' >> tower.env
echo 'LANG="en_US.UTF-8"' >> tower.env
echo 'TIMEZONE="Europe/Paris"' >> tower.env
echo 'KEYMAP="us"' >> tower.env

# sudo xinit /usr/bin/zenity --entry $* -- :0 vt1 > answer.txt