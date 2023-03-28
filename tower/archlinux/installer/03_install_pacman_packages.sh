#!/bin/bash

set -e
set -x

cp -r towerpackages /mnt
cp pacman.conf /etc/

pacstrap -K /mnt base linux linux-firmware openssh sudo \
                 iwd grub efibootmgr \
                 dhcpcd git python python-pip avahi \
                 iw base-devel docker \
                 archiso lxde xorg-xinit nano vi \
                 nxagent nxproxy nx-headers

rm -rf /mnt/towerpackages