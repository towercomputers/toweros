#!/bin/bash

set -e
set -x

ROOT_PASSWORD=$1
USERNAME=$2
PASSWORD=$3
LANG=$4
TIMEZONE=$5
KEYBOARD_LAYOUT=$6
KEYBOARD_VARIANT=$7
TARGET_DRIVE=$8

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

apk add sudo dhcpcd wpa_supplicant avahi iptables

# change root password
echo -e "$ROOT_PASSWORD\n$ROOT_PASSWORD" | passwd root
# create first user
adduser -D "$USERNAME" "$USERNAME"
echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME"
addgroup abuild || true
addgroup "$USERNAME" abuild

# TODO: set LANG
setup-timezone "$TIMEZONE"
setup-keymap "$KEYBOARD_LAYOUT" "$KEYBOARD_VARIANT"
setup-hostname -n tower

rc-update add dhcpcd
rc-update add avahi-daemon
rc-update add iptables
rc-update add wpa_supplicant boot

sh $SCRIPT_DIR/configure_firewall.sh

yes | setup-disk -m sys "$TARGET_DRIVE"

ROOT_PARTITION=$(ls $TARGET_DRIVE*3)
mount "$ROOT_PARTITION" /mnt

# save rules
iptables-save -f /mnt/etc/iptables/iptables.rules

mkdir -p "/mnt/home/$USERNAME"
mkdir "/mnt/home/$USERNAME/.ssh"
mkdir "/mnt/home/$USERNAME/.cache"
mkdir "/mnt/home/$USERNAME/.config"
echo 'export PATH=~/.local/bin:$PATH' > /home/$USERNAME/.profile
cp /mnt/var/towercomputers/docs/* /mnt/home/$USERNAME/
cp $SCRIPT_DIR/install_dev.sh /mnt/home/$USERNAME/

chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"

echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /mnt/etc/sudoers.d/01_tower_nopasswd

cat <<EOF > /mnt/etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
EOF

cat <<EOF > /etc/motd
Welcome to TowerOS-ThinClient!

Please see the ~/README.md file to know how to get started with TowerOS-ThinClient.

EOF

umount /mnt

