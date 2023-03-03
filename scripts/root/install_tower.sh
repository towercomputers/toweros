#!/bin/bash

set -e
set -x

sh 01_ask_configuration.sh
. ./tower.env

sh 02_prepare_drive.sh $TARGET_DRIVE

sh 03_install_base.sh

cp 04_update_users.sh /mnt/root/
arch-chroot /mnt sh /root/04_update_users.sh $ROOT_PASSWORD $USERNAME $PASSWORD

sh 05_install_packages.sh $USERNAME

cp 06_configure_system.sh /mnt/root/
arch-chroot /mnt sh /root/06_configure_system.sh $LANG $TIMEZONE $KEYMAP

sh 07_clean_and_reboot.sh
