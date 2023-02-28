#!/bin/bash

TARGET_DRIVE=$1

# zeroing hard drive
dd if=/dev/zero of=$TARGET_DRIVE bs=512 count=1 conv=notrunc
# create boot partition (/dev/sda1)
parted $TARGET_DRIVE mklabel gpt
parted $TARGET_DRIVE mkpart primary fat32 0% 1GB
parted $TARGET_DRIVE set 1 esp on
# create swap partition (/dev/sda2)
parted $TARGET_DRIVE mkpart primary linux-swap 1GB 9GB
# create root partition (/dev/sda3)
parted $TARGET_DRIVE mkpart primary ext4 9GB 100%
# format partitions
mkfs.fat -F 32 "${TARGET_DRIVE}1"
mkswap "${TARGET_DRIVE}2"
mkfs.ext4 -F "${TARGET_DRIVE}3"
# mount partitions
mount "${TARGET_DRIVE}3" /mnt
mount --mkdir "${TARGET_DRIVE}1" /mnt/boot
swapon "${TARGET_DRIVE}2"
