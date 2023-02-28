#!/bin/bash

set +e

WLAN_SSID="Bbox-BDC08515"
WLAN_PASSWORD=""
TARGET_DRIVE="/dev/sda"
ROOT_PASSWORD="tower"
USERNAME="tower"
PASSWORD="tower"
LANG="en_US.UTF-8"
TIMEZONE="Europe/Paris"
KEYMAP="us"

sh prepare_drive.sh $TARGET_DRIVE

# connect to internet
iwctl --passphrase $WLAN_PASSWORD station wlan0 connect $WLAN_SSID

# install packages in /mnt
pacstrap -K /mnt base linux linux-firmware \
                 iwd openssh sudo grub efibootmgr \
                 dhcpcd git python python-pip avahi \
                 iw wireless_tools base-devel docker \
                 lxde xorg-xinit

# update fstab
genfstab -U /mnt >> /mnt/etc/fstab

# copy wifi configuration
systemctl start iwd.service
mkdir /mnt/var/lib/iwd
cp /var/lib/iwd/*.psk /mnt/var/lib/iwd/

# configure as root into the new system
cp configure_system.sh /mnt/root/
arch-chroot /mnt sh /root/configure_system.sh $ROOT_PASSWORD $USERNAME $PASSWORD $LANG $TIMEZONE $KEYMAP

umount -R /mnt
reboot
