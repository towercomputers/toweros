#!/bin/bash

set -e
set -x

pacman -Sy --noconfirm \
            git openssh fakeroot sudo \
            libjpeg-turbo libpng xkeyboard-config xorg-xkbcomp xorg-xkbcomp \
            libxfont2 libxinerama xorg-font-util pixman libxrandr libxtst \
            libxcomposite libxpm libxdamage xorgproto imake patch make \
            gcc autoconf automake libtool pkg-config

git clone https://aur.archlinux.org/nx.git 
chown -R alarm:alarm nx 
cd nx 
runuser -u alarm -- makepkg -s -r -c -A --noconfirm
