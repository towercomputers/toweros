#!/bin/bash

set -e
set -x

USERNAME=$1

# install tower-tools
cp -r pippackages /mnt
arch-chroot /mnt runuser -u $USERNAME -- pip install --no-index --find-links=/pippackages \
    "x2go @ file:///pippackages/python-x2go-0.6.1.3.tar.gz" \
    gevent python-xlib requests sh backports.pbkdf2 passlib sshconf hatchling wheel
arch-chroot /mnt runuser -u $USERNAME -- pip install --no-index --find-links=/pippackages --no-deps tower-tools
