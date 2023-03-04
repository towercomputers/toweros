#!/bin/bash

set -e
set -x

sh 01_ask_configuration.sh
. ./tower.env

sh 02_prepare_drive.sh $TARGET_DRIVE

sh 03_install_pacman_packages.sh

cp 04_configure_system.sh /mnt/root/
arch-chroot /mnt sh /root/04_configure_system.sh $ROOT_PASSWORD $USERNAME $PASSWORD $LANG $TIMEZONE $KEYMAP

sh 05_install_pip_packages.sh $USERNAME

sh 06_clean_and_reboot.sh
