#!/bin/bash

set -e
set -x

pacman-key --init
pacman-key --populate archlinuxarm
pacman -Suy --noconfirm
pacman -S openssh iptables sudo python python-pip dhcpcd avahi iwd wget --noconfirm
pacman -U --arch armv7h --noconfirm /nx-armv7h/*.tar.xz