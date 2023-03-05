#!/bin/bash

set -e
set -x

rm -rf /mnt/towerpackages
rm -rf /mnt/pippackages
rm /mnt/root/04_configure_system.sh

umount -R /mnt
reboot