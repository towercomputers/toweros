#!/bin/bash

set -e
set -x

#ROOT_PASSWORD=$1
#USERNAME=$2
#PASSWORD=$3
#LANG=$4
#TIMEZONE=$5
#KEYBOARD_LAYOUT=$6
#KEYBOARD_VARIANT=$7
#TARGET_DRIVE=$8 

SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

python $SCRIPT_DIR/ask-configuration.py
source /root/tower.env

apk add sudo dhcpcd wpa_supplicant avahi iptables

# change root password
echo -e "$ROOT_PASSWORD\n$ROOT_PASSWORD" | passwd root
# create first user
adduser -D "$USERNAME" "$USERNAME"
echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME"
addgroup abuild || true
addgroup "$USERNAME" abuild

mkdir -p /etc/sudoers.d
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd

# TODO: set LANG
setup-timezone "$TIMEZONE"
setup-keymap "$KEYBOARD_LAYOUT" "$KEYBOARD_VARIANT"
setup-hostname -n tower

rc-update add dhcpcd
rc-update add avahi-daemon
rc-update add iptables
rc-update add wpa_supplicant boot

sh $SCRIPT_DIR/configure-firewall.sh

mv /var/cache/pip-packages "/home/$USERNAME/"
chown -R "$USERNAME:$USERNAME" "/home/$USERNAME/pip-packages"
runuser -u $USERNAME -- pip install --no-index --find-links="/home/$USERNAME/pip-packages" tower-tools
echo 'export PATH=~/.local/bin:$PATH' > /home/$USERNAME/.profile

cp /var/towercomputers/docs/* /home/$USERNAME/
cp $SCRIPT_DIR/install-dev.sh /home/$USERNAME/

mkdir -p /etc/network
cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
EOF

cat <<EOF > /etc/motd
Welcome to TowerOS-ThinClient!

Please see the ~/README.md file to know how to get started with TowerOS-ThinClient.

EOF

cat <<EOF > /etc/inittab
# /etc/inittab

::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default

# Set up a couple of getty's
tty1::respawn:/sbin/getty 38400 tty1
tty2::respawn:/sbin/getty 38400 tty2
tty3::respawn:/sbin/getty 38400 tty3
tty4::respawn:/sbin/getty 38400 tty4
tty5::respawn:/sbin/getty 38400 tty5
tty6::respawn:/sbin/getty 38400 tty6

# Stuff to do for the 3-finger salute
::ctrlaltdel:/sbin/reboot

# Stuff to do before rebooting
::shutdown:/sbin/openrc shutdown
EOF

rm -f /etc/profile.d/install.sh

yes | setup-disk -m sys "$TARGET_DRIVE"

ROOT_PARTITION=$(ls $TARGET_DRIVE*3)
mount "$ROOT_PARTITION" /mnt

cp -r "home/$USERNAME" "/mnt/home/"
chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"

umount /mnt
