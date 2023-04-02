#!/bin/bash

set -e
set -x

HOSTNAME="$1"
USERNAME="$2"
PUBLIC_KEY="$3"
ENCRYPTED_PASSWORD="$4"
KEYMAP="$5"
TIMEZONE="$6"
LANG="$7"
ONLINE="$8"
WLAN_SSID="$9"
WLAN_SHARED_KEY="$10"
WLAN_COUNTRY="$11"
THIN_CLIENT_IP="$12"
TOWER_NETWORK="$13"

# change root password
usermod --password "$ENCRYPTED_PASSWORD" root
# create first user
useradd -m $USERNAME -p "$ENCRYPTED_PASSWORD"
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
groupadd netdev
usermod -aG netdev $USERNAME
echo 'export PATH=~/.local/bin:$PATH' >> /home/$USERNAME/.bash_profile
# remove default user
userdel -f -r alarm
# add publick key
mkdir -p /home/$USERNAME/.ssh
echo "$PUBLIC_KEY" > /home/$USERNAME/.ssh/authorized_keys
chmod 700 /home/$USERNAME/.ssh
chmod 600 /home/$USERNAME/.ssh/*
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
systemctl enable dhcpcd.service
systemctl enable avahi-daemon.service
systemctl enable iptables.service
systemctl enable sshd.service
# enable connection
if "$ONLINE" == "true"; then
    systemctl enable iwd.service
    mkdir -p /var/lib/iwd
    echo "[Security]" > "/var/lib/iwd/$WLAN_SSID.psk"
    echo "PreSharedKey=$WLAN_SHARED_KEY" >> "/var/lib/iwd/$WLAN_SSID.psk"
fi
# configure firewall
#sh /root/configure_pi_firewall.sh $THIN_CLIENT_IP $TOWER_NETWORK