#!/bin/bash

set -e
set -x

ROOT_PASSWORD=$1
USERNAME=$2
PASSWORD=$3

LANG=$4
TIMEZONE=$5
KEYMAP=$6

HOSTNAME=$7

WLAN_SSID=$8
WLAN_PASSWORD=$9
#WLAN_PSK=PSK=$(wpa_passphrase $WLAN_SSID $WLAN_PASSWORD | grep $'\tpsk' | sed 's/\tpsk=//')

# change root password
usermod --password $(echo $ROOT_PASSWORD | openssl passwd -1 -stdin) root
# create first user
useradd -m $USERNAME -p $(echo $PASSWORD | openssl passwd -1 -stdin)
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
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
echo $HOSTNAME > /etc/hostname
# enable ipv4
sudo sed -i 's/noipv4ll/#noipv4ll/' /etc/dhcpcd.conf
# enable services
systemctl enable iwd.service
systemctl enable dhcpcd.service
systemctl enable avahi-daemon.service
systemctl enable iptables.service
systemctl enable sshd.service

PSK=$(wpa_passphrase Bbox-BDC08515 2uaUwbHN22dk6ZLFNE | grep $'\tpsk' | sed 's/\tpsk=//')
