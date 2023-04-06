#!/bin/bash

set -e
set -x

USERNAME=$1

# install tower-tools
cp -r pippackages /mnt
arch-chroot /mnt runuser -u $USERNAME -- pip install --no-index --find-links=/pippackages tower-tools

# put builds directory in `tower` cache
mkdir -p /mnt/home/$USERNAME/.cache/tower
cp -R builds /mnt/home/$USERNAME/.cache/tower/
# put install_dev.sh script in user home
cp 07_install_dev.sh /mnt/home/$USERNAME/
# fix owner
arch-chroot /mnt chown -R $USERNAME:$USERNAME /home/$USERNAME/

# clean cache
rm -rf /mnt/pippackages