#!/bin/bash

set -e
set -x

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
# get partitions names
BOOT_PARTITION=$(ls $TARGET_DRIVE*1)
SWAP_PARTITION=$(ls $TARGET_DRIVE*2)
ROOT_PARTITION=$(ls $TARGET_DRIVE*3)
# format partitions
mkfs.fat -F 32 "$BOOT_PARTITION"
mkswap "$SWAP_PARTITION"
mkfs.ext4 -F "$ROOT_PARTITION"
# mount partitions
mount "$ROOT_PARTITION" /mnt
mount --mkdir "$BOOT_PARTITION" /mnt/boot
swapon "$SWAP_PARTITION"
# update fstab
mkdir /mnt/etc/
genfstab -U /mnt > /mnt/etc/fstab
