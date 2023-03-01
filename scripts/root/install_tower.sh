#!/bin/bash

set -e

TARGET_DRIVE="/dev/sda"
ROOT_PASSWORD="tower"
USERNAME="tower"
PASSWORD="tower"
LANG="en_US.UTF-8"
TIMEZONE="Europe/Paris"
KEYMAP="us"

sh prepare_drive.sh $TARGET_DRIVE

# prepare local repo for pacstrap
cp -r towerpackages /mnt
cp pacman.conf /etc/

# install packages in /mnt
pacstrap -K /mnt base linux linux-firmware \
                 iwd openssh sudo grub efibootmgr \
                 dhcpcd git python python-pip avahi \
                 iw wireless_tools base-devel docker \
                 lxde xorg-xinit nano vi \
                 nx

# configure as root the new system
cp configure_system.sh /mnt/root/
arch-chroot /mnt sh /root/configure_system.sh $ROOT_PASSWORD $USERNAME $PASSWORD $LANG $TIMEZONE $KEYMAP

#umount -R /mnt
#reboot
