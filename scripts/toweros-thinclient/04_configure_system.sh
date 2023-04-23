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

# change root password
usermod --password $(echo $ROOT_PASSWORD | openssl passwd -1 -stdin) root
# create first user
useradd -m $USERNAME -p $(echo $PASSWORD | openssl passwd -1 -stdin)
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
groupadd netdev
usermod -aG netdev $USERNAME
echo 'export PATH=~/.local/bin:$PATH' >> /home/$USERNAME/.bash_profile
# configure fluxbox
echo "exec startfluxbox" > /home/$USERNAME/.xinitrc
mkdir -p /home/$USERNAME/.fluxbox
cp /root/fluxbox_startup /home/$USERNAME/.fluxbox/startup
cp /usr/share/fluxbox/menu /home/$USERNAME/.fluxbox/menu
sed -i 's/\[exec\] (firefox) {}/\[include\] (~\/\.fluxbox\/tower-menu)/' /home/$USERNAME/.fluxbox/menu
# put README in home folder
cp /root/README.md /home/$USERNAME/
# fix ownership
chown -R $USERNAME:$USERNAME /home/$USERNAME
# set locales
ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime
hwclock --systohc
cp /etc/locale.gen /etc/locale.gen.list
echo "$LANG UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=$LANG" > /etc/locale.conf
# configure keyboard
echo "KEYMAP=$KEYBOARD_LAYOUT" > /etc/vconsole.conf
echo "XKBLAYOUT=$KEYBOARD_LAYOUT"  >> /etc/vconsole.conf
echo "XKBVARIANT=$XKBVARIANT"  >> /etc/vconsole.conf
echo "XKBMODEL=pc105"  >> /etc/vconsole.conf
cat <<EOF > /mnt//etc/X11/xorg.conf.d/00-keyboard.conf
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "$KEYBOARD_LAYOUT"
        Option "XkbModel" "pc105"
        Option "XkbVariant" "$KEYBOARD_VARIANT"
EndSection
EOF
# set hostname
echo "tower" > /etc/hostname
# install boot loader
ROOT_PARTITION=$(ls $TARGET_DRIVE*3)
bootctl install
echo "default arch" > /boot/loader/loader.conf
echo "timeout 5" >> /boot/loader/loader.conf
echo "title   TowerOS-ThinClient" > /boot/loader/entries/arch.conf
echo "linux   /vmlinuz-linux" >> /boot/loader/entries/arch.conf
echo "initrd  /initramfs-linux.img" >> /boot/loader/entries/arch.conf
echo "options root=$ROOT_PARTITION rw" >> /boot/loader/entries/arch.conf
# enable ipv4
sed -i 's/noipv4ll/#noipv4ll/' /etc/dhcpcd.conf
# enable services
systemctl enable iwd.service
systemctl enable dhcpcd.service
systemctl enable avahi-daemon.service
systemctl enable iptables.service
# enable qemu for arm
echo ':arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-arm-static:' > /etc/binfmt.d/arm.conf
