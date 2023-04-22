#!/bin/bash

set -e
set -x

python 01_ask_configuration.py
. ./tower.env

sh 02_prepare_drive.sh $TARGET_DRIVE

sh 03_install_pacman_packages.sh

cp 04_configure_system.sh /mnt/root/
cp fluxbox_startup /mnt/root/
arch-chroot /mnt sh /root/04_configure_system.sh "$ROOT_PASSWORD" "$USERNAME" "$PASSWORD" "$LANG" "$TIMEZONE" "$KEYMAP" "$TARGET_DRIVE"
rm /mnt/root/04_configure_system.sh

cp 05_configure_firewall.sh /mnt/root/
arch-chroot /mnt sh /root/05_configure_firewall.sh
rm /mnt/root/05_configure_firewall.sh

sh 06_install_tower_tools.sh "$USERNAME"

cp welcome.msg /mnt/etc/issue

reboot
