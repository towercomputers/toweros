#!/bin/bash

set -e
set -x

ROOT_PASSWORD=$1
USERNAME=$2
PASSWORD=$3

LANG=$4
TIMEZONE=$5
KEYMAP=$6
TARGET_DRIVE=$7

# change root password
usermod --password $(echo $ROOT_PASSWORD | openssl passwd -1 -stdin) root
# create first user
useradd -m $USERNAME -p $(echo $PASSWORD | openssl passwd -1 -stdin)
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
usermod -aG docker $USERNAME
groupadd netdev
usermod -aG netdev $USERNAME
echo 'export PATH=~/.local/bin:$PATH' >> /home/$USERNAME/.bash_profile
# set locales
ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime
hwclock --systohc
cp /etc/locale.gen /etc/locale.gen.list
echo "$LANG UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=$LANG" > /etc/locale.conf
echo "KEYMAP=$KEYMAP" > /etc/vconsole.conf
# set hostname
echo "tower" > /etc/hostname
# install boot loader
ROOT_PARTITION=$(ls $TARGET_DRIVE*3)
bootctl install
echo "default arch" > /boot/loader/loader.conf
echo "timeout 5" >> /boot/loader/loader.conf
echo "title   TowerOS" > /boot/loader/entries/arch.conf
echo "linux   /vmlinuz-linux" >> /boot/loader/entries/arch.conf
echo "initrd  /initramfs-linux.img" >> /boot/loader/entries/arch.conf
echo "options root=$ROOT_PARTITION rw" >> /boot/loader/entries/arch.conf
# enable services
systemctl enable iwd.service
systemctl enable dhcpcd.service
systemctl enable avahi-daemon.service
systemctl enable docker.service
systemctl enable iptables.service
