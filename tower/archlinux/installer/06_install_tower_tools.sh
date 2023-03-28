#!/bin/bash

set -e
set -x

USERNAME=$1

# install tower-tools
cp -r pippackages /mnt
arch-chroot /mnt runuser -u $USERNAME -- pip install --no-index --find-links=/pippackages \
    "x2go @ file:///pippackages/python-x2go-0.6.1.3.tar.gz" \
    gevent python-xlib requests sh passlib sshconf hatchling wheel
arch-chroot /mnt runuser -u $USERNAME -- pip install --no-index --find-links=/pippackages --no-deps tower-tools

# put Raspbian image in `tower` cache
mkdir /mnt/home/$USERNAME/.cache/tower
cp *.xz /mnt/home/$USERNAME/.cache/tower/
arch-chroot /mnt chown -R $USERNAME:$USERNAME /home/$USERNAME/.cache/tower

# put install_dev.sh script in user home
cp install_dev.sh /mnt/home/$USERNAME/
arch-chroot /mnt chown -R $USERNAME:$USERNAME /home/$USERNAME/install_dev.sh

# clean cache
rm -rf /mnt/pippackages