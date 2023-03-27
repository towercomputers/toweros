#!/bin/bash

set -e
set -x

pacman-key --init
pacman-key --populate archlinuxarm
pacman -Suy --noconfirm
pacman -S python python-pip avahi iwd wpa_supplicant --noconfirm
pacman -U --arch armv7h --noconfirm /nx-armv7h/*.tar.xz