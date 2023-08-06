#!/bin/bash

set -e
set -x

update_passord() {
    REPLACE="$1:$2:"
    ESCAPED_REPLACE=$(printf '%s\n' "$REPLACE" | sed -e 's/[\/&]/\\&/g')
    sed -i "s/^$1:[^:]*:/$ESCAPED_REPLACE/g" /etc/shadow
}

uuid_or_device() {
	local i=
	case "$1" in
		/dev/md*) echo "$1" && return 0;;
	esac
	test -z "$USE_UUID" && echo "$1" &&return 0

	for i in $(_blkid "$1"); do
		case "$i" in
			UUID=*) eval $i;;
		esac
	done
	if [ -n "$UUID" ]; then
		echo "UUID=$UUID"
	else
		echo "$1"
	fi
}

prepare_drive() {
    # zeroing hard drive
    dd if=/dev/zero of=$TARGET_DRIVE bs=512 count=1 conv=notrunc
    # create boot partition (/dev/sda1)
    parted $TARGET_DRIVE mklabel gpt
    parted $TARGET_DRIVE mkpart primary fat32 0% 1GB
    parted $TARGET_DRIVE set 1 esp on
    # create LVM partition (/dev/sda2)
    parted $TARGET_DRIVE mkpart primary ext4 1GB 100%
    # get partitions names
    BOOT_PARTITION=$(ls $TARGET_DRIVE*1)
    LVM_PARTITION=$(ls $TARGET_DRIVE*2)
    # generate LUKS key
    #dd if=/dev/urandom of=/root/secret.key bs=1024 count=2
    #chmod 0400 /root/secret.key
    # create LUKS partition
    #cryptsetup luksFormat $LVM_PARTITION /root/secret.key
    #cryptsetup luksAddKey $LVM_PARTITION /root/secret.key --key-file=/root/secret.key
    cryptsetup -v -c aes-xts-plain64 -s 512 --hash sha512 --pbkdf pbkdf2 \
                --iter-time 1000 --use-random luksFormat $LVM_PARTITION 
    # initialize the LUKS partition
    #cryptsetup luksOpen $LVM_PARTITION lvmcrypt --key-file=/root/secret.key
    cryptsetup luksOpen $LVM_PARTITION lvmcrypt
    # create LVM physical volumes
    vgcreate vg0 /dev/mapper/lvmcrypt
    # create swap volume
    lvcreate -L 8G vg0 -n swap
    # create root volume
    lvcreate -l 100%FREE vg0 -n root
    # set partitions names
    SWAP_PARTITION="/dev/vg0/swap"
    ROOT_PARTITION="/dev/vg0/root"
    # format partitions
    mkfs.fat -F 32 "$BOOT_PARTITION"
    mkswap "$SWAP_PARTITION"
    mkfs.ext4 -F "$ROOT_PARTITION"
    # mount partitions
    mkdir -p /mnt
    mount -t ext4 "$ROOT_PARTITION" /mnt
    mkdir -p /mnt/boot
    mount "$BOOT_PARTITION" /mnt/boot
    swapon "$SWAP_PARTITION"
    # update fstab
    mkdir -p /mnt/etc/
    sh $SCRIPT_DIR/genfstab.sh /mnt > /mnt/etc/fstab
}

prepare_home_directory() {
    # create first user
    adduser -D "$USERNAME" "$USERNAME"
    update_passord "$USERNAME" "$PASSWORD_HASH"
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
}

update_live_system() {
    # set hostname
    setup-hostname -n tower

    # change root password
    update_passord "root" "$ROOT_PASSWORD_HASH"

    # configure default network
    mkdir -p /etc/network
    cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
    address 192.168.2.100/24
auto eth1
iface eth1 inet static
    address 192.168.3.100/24
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

    # start services
    rc-update add lvm
    rc-update add dmcrypt
    rc-update add iptables
    rc-update add networking
    rc-update add dbus
    rc-update add local

    # enabling udev service
    setup-devd udev

    # remove autologin from tty1
    old_tty1='tty1::respawn:\/sbin\/agetty --skip-login --nonewline --noissue --autologin root --noclear 38400 tty1'
    new_tty1='tty1::respawn:\/sbin\/getty 38400 tty1'
    sed -i "s/$old_tty1/$new_tty1/g" /etc/inittab
    # disable installer auto-start
    rm -f /etc/profile.d/install.sh

    # configure firewall
    sh $SCRIPT_DIR/configure-firewall.sh

    prepare_home_directory
}

clone_live_system_to_disk() {
    # install base system
    ovlfiles=/tmp/ovlfiles
    lbu package - | tar -C "/mnt" -zxv > $ovlfiles
    # comment out local repositories
    if [ -f /mnt/etc/apk/repositories ]; then
        sed -i -e 's:^/:#/:' /mnt/etc/apk/repositories
    fi

    # we should not try start modloop on sys install
    rm -f /mnt/etc/runlevels/*/modloop

    # generate mkinitfs.conf
    mkdir -p /mnt/etc/mkinitfs/features.d
    echo 'features="ata base ide scsi usb virtio ext4 nvme vmd lvm keymap cryptsetup cryptkey resume"' > /mnt/etc/mkinitfs/mkinitfs.conf

    # apk reads config from target root so we need to copy the config
    mkdir -p /mnt/etc/apk/keys/
    cp /etc/apk/keys/* /mnt/etc/apk/keys/

    # init chroot
    mkdir -p /mnt/proc
    mount --bind /proc /mnt/proc
    mkdir -p /mnt/dev
    mount --bind /dev /mnt/dev

    # install packages
    local apkflags="--initdb --quiet --progress --update-cache --clean-protected"
    local pkgs="$(grep -h -v -w sfdisk /mnt/etc/apk/world 2>/dev/null)"
    pkgs="$pkgs linux-lts alpine-base syslinux linux-firmware-i915 linux-firmware-intel linux-firmware-mediatek linux-firmware-other linux-firmware-rtl_bt"
    local repos="$(sed -e 's/\#.*//' "$ROOT"/etc/apk/repositories 2>/dev/null)"
    local repoflags=
    for i in $repos; do
        repoflags="$repoflags --repository $i"
    done
    apk add --root /mnt $apkflags --overlay-from-stdin $repoflags $pkgs <$ovlfiles

    # clean chroot
    umount /mnt/proc
    umount /mnt/dev

    # Get branch from buildthinclient.py
    mkdir -p /mnt/etc/apk
    cat <<EOF > /mnt/etc/apk/repositories 
http://dl-cdn.alpinelinux.org/alpine/v3.18/main
http://dl-cdn.alpinelinux.org/alpine/v3.18/community
#http://dl-cdn.alpinelinux.org/alpine/v3.18/testing
EOF

    # remove unistalled packages from xfce menu
    rm /mnt/usr/share/applications/xfce4-web-browser.desktop
    rm /mnt/usr/share/applications/xfce4-mail-reader.desktop

    # copy user's home to the new system
    cp -r "/home/$USERNAME" "/mnt/home/"
    chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"
}

install_bootloader() {
    # setup syslinux
    LVM_UUID=$(uuid_or_device $LVM_PARTITION)
    ROOT_UUID=$(uuid_or_device $ROOT_PARTITION)
    kernel_opts="quiet rootfstype=ext4 cryptroot=$LVM_UUID cryptdm=lvmcrypt"
    modules="sd-mod,usb-storage,ext4,nvme,vmd,cryptsetup,keymap,cryptkey,kms,lvm"
    sed -e "s:^root=.*:root=$ROOT_UUID:" \
        -e "s:^default_kernel_opts=.*:default_kernel_opts=\"$kernel_opts\":" \
        -e "s:^modules=.*:modules=$modules:" \
        /etc/update-extlinux.conf > /mnt/etc/update-extlinux.conf

    dd bs=440 count=1 conv=notrunc if=/usr/share/syslinux/mbr.bin of=$TARGET_DRIVE

    extlinux --install /mnt/boot
    chroot /mnt/ update-extlinux

    mkdir -p /mnt/boot/EFI/boot
    cp /usr/share/syslinux/efi64/* /mnt/boot/EFI/boot
    sed 's/\(initramfs-\|vmlinuz-\)/\/\1/g' /mnt/boot/extlinux.conf > /mnt/boot/EFI/boot/syslinux.cfg
    sed -i 's/Alpine\/Linux/TowerOS-ThinClient/g' /mnt/boot/EFI/boot/syslinux.cfg
    sed -i 's/Alpine /TowerOS-ThinClient /g' /mnt/boot/EFI/boot/syslinux.cfg
    rm -f /mnt/boot/*.c32
    rm -f /mnt/boot/*.sys
    rm -f /mnt/boot/extlinux.conf
    cp /mnt/boot/EFI/boot/syslinux.efi /mnt/boot/EFI/boot/bootx64.efi
}

install_thinclient() {
    # make sure /bin and /lib are executable
    chmod 755 /
    chmod 755 /bin
    chmod 755 /lib
    
    prepare_drive
    update_live_system
    clone_live_system_to_disk
    install_bootloader
}

unmount_and_reboot() {
    umount /mnt/boot
    umount /mnt
    reboot
}

ask_configuration() {
    SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"
    # initialize coniguration variables:
    # ROOT_PASSWORD, USERNAME, PASSWORD, LANG, TIMEZONE, KEYBOARD_LAYOUT, KEYBOARD_VARIANT, TARGET_DRIVE
    python $SCRIPT_DIR/ask-configuration.py
    source /root/tower.env
}

ask_configuration
install_thinclient
unmount_and_reboot