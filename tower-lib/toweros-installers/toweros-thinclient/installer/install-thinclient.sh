#!/bin/bash

set -e
set -x

update_passord() {
    REPLACE="$1:$2:"
    ESCAPED_REPLACE=$(printf '%s\n' "$REPLACE" | sed -e 's/[\/&]/\\&/g')
    sed -i "s/^$1:[^:]*:/$ESCAPED_REPLACE/g" /etc/shadow
}

initialize_disks() {
    # zeroing root drive
    dd if=/dev/zero of=$TARGET_DRIVE bs=512 count=1 conv=notrunc
    parted $TARGET_DRIVE mklabel gpt
    # zeroing boot drive
    dd if=/dev/zero of=$CRYPTKEY_DRIVE bs=512 count=1 conv=notrunc
    parted $CRYPTKEY_DRIVE mklabel gpt
}

prepare_boot_partition() {
    # create boot partition
    parted $CRYPTKEY_DRIVE mkpart primary fat32 0% 100%
    parted $CRYPTKEY_DRIVE set 1 esp on
    # get partition name
    BOOT_PARTITION=$(ls $CRYPTKEY_DRIVE*1)
}

prepare_lvm_partition() {
    # create LVM partition (/dev/sda2)
    parted $TARGET_DRIVE mkpart primary ext4 0% 100%
    # get partition name
    LVM_PARTITION=$(ls $TARGET_DRIVE*1)
    # generate LUKS key
    dd if=/dev/urandom of=/crypto_keyfile.bin bs=1024 count=2
    chmod 0400 /crypto_keyfile.bin
    # create LUKS partition
    cryptsetup -q luksFormat $LVM_PARTITION /crypto_keyfile.bin
    cryptsetup luksAddKey $LVM_PARTITION /crypto_keyfile.bin --key-file=/crypto_keyfile.bin
    # initialize the LUKS partition
    cryptsetup luksOpen $LVM_PARTITION lvmcrypt --key-file=/crypto_keyfile.bin
    # create LVM physical volumes
    vgcreate -ff -y vg0 /dev/mapper/lvmcrypt 
}

check_and_copy_key_from_boot_disk() {
    BOOT_PARTITION=$(ls $CRYPTKEY_DRIVE*1)
    if ! [ -b "$BOOT_PARTITION" ]; then
        echo "Boot partition not found"
        exit 1
    fi
    mkdir -p /BOOTKEY
    mount "$BOOT_PARTITION" /BOOTKEY
    if ! [ -f "/BOOTKEY/crypto_keyfile.bin" ]; then
        echo "Key file not found in boot partition"
        exit 1
    fi
    LVM_PARTITION=$(ls $TARGET_DRIVE*1)
    if ! [ -b "$LVM_PARTITION" ]; then
        echo "Target partition not found"
        exit 1
    fi
    key_is_ok=$(cryptsetup luksOpen --key-file /BOOTKEY/crypto_keyfile.bin --test-passphrase $LVM_PARTITION && echo "OK" || echo "NOK")
    if [ "$key_is_ok" == "NOK" ]; then
        echo "Key file is not valid"
        exit 1
    fi
    cp /BOOTKEY/crypto_keyfile.bin /crypto_keyfile.bin
    chmod 0400 /crypto_keyfile.bin
    umount /BOOTKEY
}

set_config_from_root_partition() {
    mkdir -p /ROOT
    mount -t ext4 "$ROOT_PARTITION" /ROOT
    # set username
    USERNAME=$(cat /ROOT/etc/sudoers.d/01_tower_nopasswd | awk '{print $1}')
    # set user password hash
    PASSWORD_HASH=$(cat /ROOT/etc/shadow | grep $USERNAME | cut -d ':' -f 2)
    # set root password hash
    ROOT_PASSWORD_HASH=$(cat /ROOT/etc/shadow | grep root | cut -d ':' -f 2)
    # set keyboard layout and variant
    KEYBOARD_LAYOUT=$(cat /ROOT/etc/vconsole.conf | grep XKBLAYOUT | cut -d '=' -f 2)
    KEYBOARD_VARIANT=$(cat /ROOT/etc/vconsole.conf | grep XKBVARIANT | cut -d '=' -f 2)
    # set timezone
    region=$(ls -al /ROOT/etc/localtime | cut -d '>' -f 2 | cut -d '/' -f 4)
    zone=$(ls -al /ROOT/etc/localtime | cut -d '>' -f 2 | cut -d '/' -f 5)
    TIMEZONE="$region/$zone"
    # set secure boot
    if [ -d /ROOT/mnt/usr/share/secureboot ]; then
        SECURE_BOOT="true"
    else
        SECURE_BOOT="false"
    fi
    # set startx on login
    STARTX_ON_LOGIN="false" # in any case, already present in /home if needed
    umount /ROOT
}

create_root_disk() {
    initialize_disks
    prepare_boot_partition
    prepare_lvm_partition
    # create swap volume
    lvcreate -y -L 8G vg0 -n swap
    # create home volume
    lvcreate -y -l 20%FREE vg0 -n home
    # create root volume
    lvcreate -y -l 100%FREE vg0 -n root
    # set partitions names
    SWAP_PARTITION="/dev/vg0/swap"
    HOME_PARTITION="/dev/vg0/home"
    ROOT_PARTITION="/dev/vg0/root"
}

activate_root_disk() {
    # initialize the LUKS partition
    cryptsetup luksOpen $LVM_PARTITION lvmcrypt --key-file=/crypto_keyfile.bin
    vgchange -ay vg0
    # set partitions names
    SWAP_PARTITION="/dev/vg0/swap"
    HOME_PARTITION="/dev/vg0/home"
    ROOT_PARTITION="/dev/vg0/root"
}

prepare_drive() {
    if [ "$INSTALLATION_TYPE" == "install" ]; then
        create_root_disk
    fi
    # format partitions
    mkfs.fat -F 32 "$BOOT_PARTITION"
    mkswap "$SWAP_PARTITION"
    # don't format home partition if we are updating the system
    if [ "$INSTALLATION_TYPE" == "install" ]; then
        mkfs.ext4 -F "$HOME_PARTITION"
    fi
    mkfs.ext4 -F "$ROOT_PARTITION"
    # mount partitions
    mkdir -p /mnt
    mount -t ext4 "$ROOT_PARTITION" /mnt
    mkdir -p /mnt/boot
    mount "$BOOT_PARTITION" /mnt/boot
    mkdir -p /mnt/home
    mount "$HOME_PARTITION" /mnt/home
    swapon "$SWAP_PARTITION"
    # update fstab
    mkdir -p /mnt/etc/
    sh $SCRIPT_DIR/genfstab.sh /mnt > /mnt/etc/fstab
    # remove boot partition from fstab
    sed -i '/\/boot/d' /mnt/etc/fstab
    # copy LUKS key to the disk
    cp /crypto_keyfile.bin /mnt/crypto_keyfile.bin
    # copy LUKS key to the boot disk
    cp /crypto_keyfile.bin /mnt/boot/crypto_keyfile.bin
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
    # create .Xauthority file
    touch /home/$USERNAME/.Xauthority
    # start X on login if necessary
    if [ "$STARTX_ON_LOGIN" == "true" ]; then
        echo 'if [ -z "$DISPLAY" ] && [ "$(tty)" == "/dev/tty1" ]; then startx; fi' >> /home/$USERNAME/.profile
    fi
}

install_tower_tools() {
    TOWER_FOLDER=/mnt/var/towercomputers
    mkdir -p $TOWER_FOLDER
    # put documentation and install-dev.sh in Tower folder
    cp -r /var/towercomputers/docs $TOWER_FOLDER
    ln -s /var/towercomputers/docs /home/$USERNAME/docs
    cp $SCRIPT_DIR/install-dev.sh $TOWER_FOLDER
    # put toweros builds in Tower folder
    cp -r /var/towercomputers/builds $TOWER_FOLDER

    # install tower with pip
    pip install --root="/mnt" --no-index --no-warn-script-location --find-links="/var/cache/pip-packages" tower-lib
    pip install --root="/mnt" --no-index --no-warn-script-location --find-links="/var/cache/pip-packages" --no-deps tower-cli
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
    #gateway 192.168.2.1
auto eth1
iface eth1 inet static
    address 192.168.3.100/24
EOF
    # For devs convenience
    cat <<EOF > /etc/resolv.conf
#nameserver 8.8.8.8
#nameserver 8.8.4.4
EOF

    # ensure eth0 exists and that it's always eth0
    if [  ! -f /sys/class/net/eth0/address ]; then
        echo "eth0 not found"
        exit 1
    fi
    INSTALL_ETH0_MAC=$(cat /sys/class/net/eth0/address)
    cat <<EOF > /etc/local.d/01_check_ifnames.start
INSTALL_ETH0_MAC=$INSTALL_ETH0_MAC
BOOT_ETH0_MAC=\$(cat /sys/class/net/eth0/address)
# we assume that if the mac has changed it is because there is an eth1
if [ ! \$INSTALL_ETH0_MAC == \$BOOT_ETH0_MAC ]; then
    ip link set eth0 down
    ip link set eth1 down
    ip link set eth0 name tmp0
    ip link set eth1 name eth0
    ip link set tmp0 name eth1
    rc-service networking restart
fi
EOF
    chmod a+x /etc/local.d/01_check_ifnames.start

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

    # disable wireless devices
    rfkill block all

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

    features="ata base ide scsi usb virtio vfat ext4 nvme vmd lvm keymap"
    features="$features cryptsetup cryptkey resume"
    echo "features=\"$features\"" > /mnt/etc/mkinitfs/mkinitfs.conf

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
    cp -rf "/home/$USERNAME" "/mnt/home/"
    chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"
}

install_bootloader() {
    # https://madaidans-insecurities.github.io/guides/linux-hardening.html#result
    kernel_opts="quiet rootfstype=ext4 slab_nomerge init_on_alloc=1 init_on_free=1 page_alloc.shuffle=1 pti=on vsyscall=none debugfs=off oops=panic module.sig_enforce=1 lockdown=confidentiality mce=0 loglevel=0"
    modules="sd-mod,usb-storage,vfat,ext4,nvme,vmd,keymap,kms,lvm"
    # add cryptsetup and cryptkey to kernel options
    kernel_opts="$kernel_opts cryptroot=$LVM_PARTITION cryptkey=yes cryptdm=lvmcrypt"
    modules="$modules,cryptsetup,cryptkey"

    # setup syslinux
    sed -e "s:^root=.*:root=$ROOT_PARTITION:" \
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

install_secure_boot() {
    if [ "$SECURE_BOOT" = "true" ]; then
        sbctl create-keys
        cp /mnt/boot/EFI/boot/bootx64.efi /mnt/boot/EFI/boot/bootx64.efi.unsigned
        sbctl sign /mnt/boot/EFI/boot/bootx64.efi
        sbctl enroll-keys -m
        mkdir -p /mnt/usr/share/secureboot
        cp -rf /usr/share/secureboot/* /mnt/usr/share/secureboot/
    fi
}

install_thinclient() {
    # make sure /bin and /lib are executable
    chmod 755 /
    chmod 755 /bin
    chmod 755 /lib
    
    prepare_drive
    update_live_system
    install_tower_tools
    clone_live_system_to_disk
    install_bootloader
    install_secure_boot
}

unmount_and_reboot() {
    rm -f /mnt/crypto_keyfile.bin
    umount /mnt/boot
    umount /mnt/home
    umount /mnt
    python $SCRIPT_DIR/end-installation.py
    reboot
}

set_configuration() {
    SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"
    # initialize coniguration variables:
    # INSTALLATION_TYPE, ROOT_PASSWORD_HASH, USERNAME, PASSWORD_HASH,
    # LANG, TIMEZONE, KEYBOARD_LAYOUT, KEYBOARD_VARIANT,
    # TARGET_DRIVE, CRYPTKEY_DRIVE, SECURE_BOOT
    # STARTX_ON_LOGIN
    python $SCRIPT_DIR/ask-configuration.py
    source /root/tower.env
    if [ "$INSTALLATION_TYPE" == "update" ]; then
        check_and_copy_key_from_boot_disk
        activate_root_disk
        set_config_from_root_partition
    fi
}

set_configuration
install_thinclient
unmount_and_reboot