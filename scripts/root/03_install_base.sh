#!/bin/bash

set -e
set -x

cp -r towerpackages /mnt
cp pacman.conf /etc/
pacstrap -K /mnt base linux linux-firmware openssh sudo