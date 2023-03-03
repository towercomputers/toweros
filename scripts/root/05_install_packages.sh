#!/bin/bash

set -e
set -x

USERNAME=$1

# prepare local repo for pacstrap and pip
cp -r towerpackages /mnt
cp pacman.conf /etc/
cp -r pippackages /mnt

# install pacman packages in /mnt
pacstrap -K /mnt iwd openssh sudo grub efibootmgr \
                 dhcpcd git python python-pip avahi \
                 iw wireless_tools base-devel docker \
                 archiso lxde xorg-xinit nano vi \
                 nxagent nxproxy nx-headers

# install tower-tools
arch-chroot /mnt runuser -u $USERNAME -- pip install --no-index --find-links=/pippackages \
    "x2go @ file:///pippackages/python-x2go-0.6.1.3.tar.gz" \
    gevent python-xlib requests sh backports.pbkdf2 passlib sshconf hatchling wheel
arch-chroot /mnt runuser -u $USERNAME -- pip install --no-index --find-links=/pippackages --no-deps tower-tools
