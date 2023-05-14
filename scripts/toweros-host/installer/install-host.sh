#!/bin/sh

set -e
set +x

# tower.env MUST contains the following variables:
# HOSTNAME, USERNAME, PUBLIC_KEY, PASSWORD, KEYBOARD_LAYOUT, KEYBOARD_VARIANT, 
# TIMEZONE, LANG, ONLINE, WLAN_SSID, WLAN_SHARED_KEY, THIN_CLIENT_IP, TOWER_NETWORK
source /media/mmcblk0p1/tower.env

SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

# create mount point
mkdir -p /mnt
# fix root partition if necessary
e2fsck -y /dev/mmcblk0p2 || true
# mount root partition
mount /dev/mmcblk0p2 /mnt

# TODO: set locale
setup-hostname -n $HOSTNAME
setup-keymap $KEYBOARD_LAYOUT $KEYBOARD_VARIANT
setup-timezone $TIMEZONE

# change root password
echo -e "$PASSWORD\n$PASSWORD" | passwd root
# create first user
adduser -D "$USERNAME" "$USERNAME"
echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME"
# add user to sudoers
mkdir -p /etc/sudoers.d
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
# add publick key
mkdir -p /home/$USERNAME/.ssh
echo "$PUBLIC_KEY" > /home/$USERNAME/.ssh/authorized_keys
chown -R $USERNAME:$USERNAME /home/$USERNAME
chmod 700 /home/$USERNAME/.ssh
chmod 600 /home/$USERNAME/.ssh/*

# configure firewall
sh $SCRIPT_DIR/configure-firewall.sh "$THIN_CLIENT_IP" "$TOWER_NETWORK" "$ONLINE"

# configure default network
cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
EOF

# enable connection if requested
if "$ONLINE" == "true"; then
mkdir -p /etc/wpa_supplicant
cat <<EOF > /etc/wpa_supplicant/wpa_supplicant.conf
network={
	ssid="$WLAN_SSID"
	psk=$WLAN_SHARED_KEY
}
EOF
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
# update network configuration
echo "auto wlan0" >> /etc/network/interfaces
echo "iface wlan0 inet dhcp" >> /etc/network/interfaces
fi

# TODO: more sshd configuration
# Allow tcp forwarding for ssh tunneling (used by `instlall` and `run` commands)
sed -i 's/AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config

# setup services
rc-update add iptables default
rc-update add dhcpcd default
rc-update add dbus default
rc-update add avahi-daemon default
rc-update add sshd default
rc-update add wpa_supplicant boot
rc-update add networking boot

# install alpine system in /mnt
export FORCE_BOOTFS=1
yes | setup-disk -m sys /mnt

# prepare boot and root partitions and folders
mount -o remount,rw /media/mmcblk0p1
rm -f /media/mmcblk0p1/boot/* 
rm /mnt/boot/boot
mv /mnt/boot/* /media/mmcblk0p1/boot/
rm -Rf /mnt/boot
mkdir /mnt/media/mmcblk0p1
ln -s /mnt/media/mmcblk0p1/boot /mnt/boot || true
# update fstab
echo "/dev/mmcblk0p1 /media/mmcblk0p1 vfat defaults 0 0" >> /mnt/etc/fstab
sed -i '/cdrom/d' /mnt/etc/fstab 
sed -i '/floppy/d' /mnt/etc/fstab
# update cmdline.txt
sed -i 's/$/ root=\/dev\/mmcblk0p2 /' /media/mmcblk0p1/cmdline.txt

# disable auto installation on boot
mv /mnt/etc/local.d/install-host.start /mnt/etc/local.d/install.bak || true

# copy home directory in /mnt
mkdir -p "/mnt/home/"
cp -r "/home/$USERNAME" "/mnt/home/"
chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"

# Get branch from buildhost.py
# configure apk repositories if host is online
if "$ONLINE" == "true"; then
mkdir -p /mnt/etc/apk
cat <<EOF > /mnt/etc/apk/repositories 
http://dl-cdn.alpinelinux.org/alpine/v3.17/main
http://dl-cdn.alpinelinux.org/alpine/v3.17/community
#http://dl-cdn.alpinelinux.org/alpine/v3.17/testing
EOF
fi

# remove configuration file
rm /media/mmcblk0p1/tower.env

reboot