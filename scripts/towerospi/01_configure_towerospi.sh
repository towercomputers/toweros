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
WLAN_SHARED_KEY="${10}"
THIN_CLIENT_IP="${11}"
TOWER_NETWORK="${12}"

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
chown -R $USERNAME:$USERNAME /home/$USERNAME
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
# disable avahi for wlan
sudo sed -i 's/#allow-interfaces=eth0/allow-interfaces=end0/' /etc/avahi/avahi-daemon.conf
sudo sed -i 's/#deny-interfaces=eth1/deny-interfaces=wlan0/' /etc/avahi/avahi-daemon.conf
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
ESCAPED_TOWER_NETWORK=$(printf '%s\n' "$TOWER_NETWORK" | sed -e 's/[\/&]/\\&/g')
sed -e "s/THIN_CLIENT_IP/$THIN_CLIENT_IP/g" \
    -e "s/TOWER_NETWORK/$ESCAPED_TOWER_NETWORK/g" \
    /root/towerospi_iptables.rules > /etc/iptables/iptables.rules