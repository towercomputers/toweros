#!/bin/bash

set -e
set -x

cp -r pacman-packages /mnt
cp pacman.conf /etc/

pacstrap -K /mnt $(cat packages.x86_64)

rm -rf /mnt/pacman-packages