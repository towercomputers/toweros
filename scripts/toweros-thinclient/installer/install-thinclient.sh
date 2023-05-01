#!/bin/bash

set -e
set -x

SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

# initialize coniguration variables:
# ROOT_PASSWORD, USERNAME, PASSWORD, LANG, TIMEZONE, KEYBOARD_LAYOUT, KEYBOARD_VARIANT, TARGET_DRIVE
python $SCRIPT_DIR/ask-configuration.py
source /root/tower.env

# change root password
echo -e "$ROOT_PASSWORD\n$ROOT_PASSWORD" | passwd root
# create first user
adduser -D "$USERNAME" "$USERNAME"
echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME"
# add user to abuild group (necessary for building packages)
addgroup abuild || true
addgroup "$USERNAME" abuild
# add user to sudoers
mkdir -p /etc/sudoers.d
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd

# set locales
# TODO: set LANG
setup-timezone "$TIMEZONE"
setup-keymap "$KEYBOARD_LAYOUT" "$KEYBOARD_VARIANT"
# set hostname
setup-hostname -n tower
# start services
rc-update add dhcpcd
rc-update add avahi-daemon
rc-update add iptables
rc-update add wpa_supplicant boot
# configure firewall
sh $SCRIPT_DIR/configure-firewall.sh

# install tower-tools with pip
mv /var/cache/pip-packages "/home/$USERNAME/"
chown -R "$USERNAME:$USERNAME" "/home/$USERNAME/pip-packages"
runuser -u $USERNAME -- pip install --no-index --find-links="/home/$USERNAME/pip-packages" tower-tools
echo 'export PATH=~/.local/bin:$PATH' > /home/$USERNAME/.profile
# put documentation and install-dev.sh in user's home
cp /var/towercomputers/docs/* /home/$USERNAME/
cp $SCRIPT_DIR/install-dev.sh /home/$USERNAME/

# configure default network
mkdir -p /etc/network
cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
EOF
# configure welcome messages
cat <<EOF > /etc/issue
Welcome to TowerOS-ThinClient!

Please see the ~/README.md file to know how to get started with TowerOS-ThinClient.

EOF
rm -f /etc/motd
touch /etc/motd

# remove autologin from tty1
old_tty1='tty1::respawn:\/sbin\/agetty --skip-login --nonewline --noissue --autologin root --noclear 38400 tty1'
new_tty1='tty1::respawn:\/sbin\/getty 38400 tty1'
sed -i "s/$old_tty1/$new_tty1/g" /etc/inittab
# disable installer auto-start
rm -f /etc/profile.d/install.sh

# launch setup-disk
yes | setup-disk -m sys "$TARGET_DRIVE"

# copy user's home to the new system
ROOT_PARTITION=$(ls $TARGET_DRIVE*3)
mount "$ROOT_PARTITION" /mnt
cp -r "/home/$USERNAME" "/mnt/home/"
chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"

# unmount and reboot
umount /mnt
reboot
