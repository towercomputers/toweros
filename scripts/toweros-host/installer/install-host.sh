#!/bin/sh

set -e
set +x

#HOSTNAME="office"
#USERNAME="tower"
#PUBLIC_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJMdPXjBDbI7fV4ieSkT9GJZghyXtcmuS1oiI6qLils2 air"
#PASSWORD='tower'
#KEYBOARD_LAYOUT="fr" 
#KEYBOARD_VARIANT="fr"
#TIMEZONE="Europe/Paris"
#LANG="en_US.UTF-8"
#ONLINE="true"
#WLAN_SSID="Bbox-BDC08515"
#WLAN_SHARED_KEY="981b4bf7bdd52cb22619e78cdf15bc7dfbe3adcc67ed4fb0525c51bc0404839d"
#THIN_CLIENT_IP="169.254.243.65"
#TOWER_NETWORK="169.254.0.0/16"

source /media/mmcblk0p1/tower.env

SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

mkdir -p /mnt
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

sh $SCRIPT_DIR/configure-firewall.sh $THIN_CLIENT_IP $TOWER_NETWORK

cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
EOF

# enable connection
if "$ONLINE" == "true"; then
mkdir -p /etc/wpa_supplicant
cat <<EOF > /etc/wpa_supplicant/wpa_supplicant.conf
network={
	ssid="$WLAN_SSID"
	psk=$WLAN_SHARED_KEY
}
EOF
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
echo "auto wlan0" >> /etc/network/interfaces
echo "iface wlan0 inet dhcp" >> /etc/network/interfaces
fi

# TODO: more sshd configuration
sed -i 's/AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config

rc-update add iptables default
rc-update add dhcpcd default
rc-update add dbus default
rc-update add avahi-daemon default
rc-update add sshd default
rc-update add wpa_supplicant boot
rc-update add networking boot

export FORCE_BOOTFS=1
yes | setup-disk -m sys /mnt
mount -o remount,rw /media/mmcblk0p1

rm -f /media/mmcblk0p1/boot/* 

rm /mnt/boot/boot

mv /mnt/boot/* /media/mmcblk0p1/boot/
rm -Rf /mnt/boot
mkdir /mnt/media/mmcblk0p1
ln -s /mnt/media/mmcblk0p1/boot /mnt/boot || true

echo "/dev/mmcblk0p1 /media/mmcblk0p1 vfat defaults 0 0" >> /mnt/etc/fstab
sed -i '/cdrom/d' /mnt/etc/fstab 
sed -i '/floppy/d' /mnt/etc/fstab

sed -i 's/$/ root=\/dev\/mmcblk0p2 /' /media/mmcblk0p1/cmdline.txt

mv /mnt/etc/local.d/install-host.start /mnt/etc/local.d/install.bak || true

mkdir -p "/mnt/home/"
cp -r "/home/$USERNAME" "/mnt/home/"
chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"

reboot