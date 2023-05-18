#!/bin/bash

set -e
set -x

# make sure /bin and /lib are executable
chmod 755 /
chmod 755 /bin
chmod 755 /lib

SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

# initialize coniguration variables:
# ROOT_PASSWORD, USERNAME, PASSWORD, LANG, TIMEZONE, KEYBOARD_LAYOUT, KEYBOARD_VARIANT, TARGET_DRIVE
python $SCRIPT_DIR/ask-configuration.py
source /root/tower.env

# set hostname
setup-hostname -n tower

# change root password
echo -e "$ROOT_PASSWORD\n$ROOT_PASSWORD" | passwd root
# create first user
adduser -D "$USERNAME" "$USERNAME"
echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME"
# add user to abuild group (necessary for building packages)
addgroup abuild || true
addgroup "$USERNAME" abuild
# add user to groups needed by xorg
addgroup "$USERNAME" video
addgroup "$USERNAME" audio
addgroup "$USERNAME" input
# add user to sudoers
mkdir -p /etc/sudoers.d
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd

# put documentation and install-dev.sh in user's home
cp -r /var/towercomputers/docs /home/$USERNAME/
cp $SCRIPT_DIR/install-dev.sh /home/$USERNAME/
# put setup-wifi script in $PATH
mkdir -p /home/$USERNAME/.local/bin
cp $SCRIPT_DIR/setup-wifi /home/$USERNAME/.local/bin/
# put tower-tools wheel in user's tower cache dir
mkdir -p /home/$USERNAME/.cache/tower/builds
cp /var/towercomputers/builds/* /home/$USERNAME/.cache/tower/builds/
# create .Xauthority file
touch /home/$USERNAME/.Xauthority

# install tower-tools with pip
mv /var/cache/pip-packages "/home/$USERNAME/"
chown -R "$USERNAME:$USERNAME" "/home/$USERNAME/"
runuser -u $USERNAME -- pip install --no-index --no-warn-script-location --find-links="/home/$USERNAME/pip-packages" tower-tools
echo 'export PATH=~/.local/bin:$PATH' > /home/$USERNAME/.profile

# configure default network
mkdir -p /etc/network
cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
EOF

# set locales
# TODO: set LANG
setup-timezone "$TIMEZONE"
setup-keymap "$KEYBOARD_LAYOUT" "$KEYBOARD_VARIANT"

# configure keyboard
echo "KEYMAP=$KEYBOARD_LAYOUT" > /etc/vconsole.conf
echo "XKBLAYOUT=$KEYBOARD_LAYOUT"  >> /etc/vconsole.conf
echo "XKBVARIANT=$KEYBOARD_VARIANT"  >> /etc/vconsole.conf
echo "XKBMODEL=pc105"  >> /etc/vconsole.conf
mkdir -p /etc/X11/xorg.conf.d
cat <<EOF > /etc/X11/xorg.conf.d/00-keyboard.conf
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "$KEYBOARD_LAYOUT"
        Option "XkbModel" "pc105"
        Option "XkbVariant" "$KEYBOARD_VARIANT"
EndSection
EOF

# remove unistalled packages from xfce menu
rm /usr/share/applications/xfce4-web-browser.desktop
rm /usr/share/applications/xfce4-mail-reader.desktop

# start services
rc-update add dhcpcd
rc-update add avahi-daemon
rc-update add iptables
rc-update add networking
rc-update add wpa_supplicant boot
rc-update add dbus
rc-update add local

# enabling udev service
setup-devd udev

# configure firewall
sh $SCRIPT_DIR/configure-firewall.sh

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

# Get branch from buildthinclient.py
mkdir -p /mnt/etc/apk
cat <<EOF > /mnt/etc/apk/repositories 
http://dl-cdn.alpinelinux.org/alpine/v3.18/main
http://dl-cdn.alpinelinux.org/alpine/v3.18/community
#http://dl-cdn.alpinelinux.org/alpine/v3.18/testing
EOF

# unmount and reboot
umount /mnt
reboot
