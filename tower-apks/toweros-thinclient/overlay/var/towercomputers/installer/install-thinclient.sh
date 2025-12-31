#!/bin/bash

set -e
set -x

ARCH="$(arch)"

update_passord() {
    REPLACE="$1:$2:"
    ESCAPED_REPLACE=$(printf '%s\n' "$REPLACE" | sed -e 's/[\/&]/\\&/g')
    sed -i "s/^$1:[^:]*:/$ESCAPED_REPLACE/g" /etc/shadow
}


initialize_disks() {
    # zeroing root device
    dd if=/dev/zero of=$TARGET_DRIVE bs=512 count=1 conv=notrunc
    parted $TARGET_DRIVE mklabel gpt
    # zeroing boot device
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
    modprobe xchacha20
    modprobe adiantum
    modprobe nhpoly1305
    cryptsetup -q luksFormat -c xchacha12,aes-adiantum-plain64 $LVM_PARTITION /crypto_keyfile.bin
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
    USERNAME=$(cat /ROOT/etc/doas.conf | awk '{print $3}')
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
    STARTW_ON_LOGIN="false" # in any case, already present in /home if needed
    # get installed packages
    ALL_INSTALLED_PACKAGES=$(cat /ROOT/etc/apk/world)
    INSTALLED_PACKAGES=""
    for package in $ALL_INSTALLED_PACKAGES; do
        if [[ ! "$DEFAULT_PACKAGES" == *"$package"* ]]; then
            INSTALLED_PACKAGES="$INSTALLED_PACKAGES $package"
        fi
    done
    # copy ETH0_MAC if exists
    if [ -f /ROOT/etc/local.d/eth0_mac ]; then
        cp /ROOT/etc/local.d/eth0_mac /etc/local.d/eth0_mac
        sh /etc/local.d/01_init_network.start
    fi
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


configure_user() {
    # change root password
    update_passord "root" "$ROOT_PASSWORD_HASH"
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
    addgroup "$USERNAME" seat
    chsh "$USERNAME" -s /bin/bash
    # add user to doas config
    echo "permit nopass $USERNAME as root" > /etc/doas.conf
    # create home directory
    mkdir -p "/mnt/home/$USERNAME" 
    # create symlink to doc
    ln -s /var/towercomputers/docs /mnt/home/$USERNAME/docs || true
    # create empty widget if not exists
    mkdir -p /mnt/home/$USERNAME/.local/tower
    touch /mnt/home/$USERNAME/.local/tower/tower.widget
    # initialize osconfig file
    if [ "$STARTW_ON_LOGIN" == "true" ]; then
        echo "STARTW_ON_LOGIN='true'" > /mnt/home/$USERNAME/.local/tower/osconfig
    fi
    # set ownership
    chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"
    # copy ETH0_MAC if exists
    mkdir -p /mnt/etc/local.d
    cp /etc/local.d/eth0_mac /mnt/etc/local.d/ || true
    # install user abuild keys
    if [ -d /mnt/home/$USERNAME/.abuild ]; then
        mkdir -p /mnt/etc/apk/keys/
        cp /mnt/home/$USERNAME/.abuild/*.pub /mnt/etc/apk/keys/
    fi
}


configure_locales() {
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
}


disable_installer() {
    # remove autologin from tty1
    old_tty1='tty1::respawn:\/sbin\/agetty --skip-login --nonewline --noissue --autologin root --noclear 38400 tty1'
    new_tty1='tty1::respawn:\/sbin\/getty 38400 tty1'
    sed -i "s/$old_tty1/$new_tty1/g" /etc/inittab

    # disable installer auto-start
    rm -f /etc/profile.d/install.sh
}


update_live_system() {
    configure_user
    configure_locales
    disable_installer
}


generate_mkinitfs() {
    mkdir -p /mnt/etc/mkinitfs/features.d
    features="base usb vfat ext4 nvme vmd lvm cryptsetup cryptkey kms"
    features="$features ata ide scsi mmc virtio keymap resume"
    echo "features=\"$features\"" > /mnt/etc/mkinitfs/mkinitfs.conf
}


clone_live_system_to_disk() {
    # backup local config in apkovl
    ovlfiles=/tmp/ovlfiles
    lbu package - | tar -C "/mnt" -zxv > $ovlfiles

    generate_mkinitfs

    # copy apk keys
    mkdir -p /mnt/etc/apk/keys/
    cp /etc/apk/keys/* /mnt/etc/apk/keys/

    # init chroot
    mkdir -p /mnt/proc
    mount --bind /proc /mnt/proc
    mkdir -p /mnt/dev
    mount --bind /dev /mnt/dev

    # install packages
    local apkflags="--quiet --progress --update-cache --clean-protected"
    # local repos
    local repos="$(sed -e 's/\#.*//' "$ROOT"/etc/apk/repositories 2>/dev/null)"
    local repoflags=
    for i in $repos; do
        repoflags="$repoflags --repository $i"
    done
    # install packages in /mnt
    apk add --root /mnt $apkflags --initdb --overlay-from-stdin --force-overwrite $repoflags $DEFAULT_PACKAGES <$ovlfiles

    # clean chroot
    umount /mnt/proc
    umount /mnt/dev

    # configure apk repositories
	mkdir -p /mnt/etc/apk
	cat <<EOF > /mnt/etc/apk/repositories
http://dl-cdn.alpinelinux.org/alpine/$ALPINE_BRANCH/main
http://dl-cdn.alpinelinux.org/alpine/$ALPINE_BRANCH/community
#http://dl-cdn.alpinelinux.org/alpine/edge/testing
EOF

    # disable modloop in /mnt
    rm -f /mnt/etc/runlevels/sysinit/modloop
}


install_bootloader() {
    # https://madaidans-insecurities.github.io/guides/linux-hardening.html#result
    kernel_opts="quiet rootfstype=ext4 slab_nomerge init_on_alloc=1 init_on_free=1 page_alloc.shuffle=1 pti=on vsyscall=none debugfs=off oops=panic module.sig_enforce=1 lockdown=confidentiality mce=0 loglevel=0"
    kernel_opts="$kernel_opts root=$ROOT_PARTITION cryptroot=$LVM_PARTITION cryptkey=yes cryptdm=lvmcrypt"
    modules="loop,squashfs,sd-mod,usb-storage,vfat,ext4,nvme,vmd,kms,lvm,cryptsetup,cryptkey,keymap"
    # x86_64
    if [ "$ARCH" == "x86_64" ]; then
         # setup syslinux
        sed -e "s:^root=.*:root=$ROOT_PARTITION:" \
            -e "s:^default_kernel_opts=.*:default_kernel_opts=\"$kernel_opts\":" \
            -e "s:^modules=.*:modules=$modules:" \
            /etc/update-extlinux.conf > /mnt/etc/update-extlinux.conf
        # write MBR
        dd bs=440 count=1 conv=notrunc if=/usr/share/syslinux/mbr.bin of=$TARGET_DRIVE
        # install syslinux
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
    # RPI
    elif [ "$ARCH" == "aarch64" ]; then
        # update cmdline.txt
        kernel_opts="console=tty1 $kernel_opts"
        cmdline="modules=$modules $kernel_opts"
        echo "$cmdline" > /mnt/boot/cmdline.txt
    fi
}


install_secure_boot() {
    if [ "$SECURE_BOOT" == "true" ] && [ "$ARCH" == "x86_64" ]; then
        sbctl create-keys
        cp /mnt/boot/EFI/boot/bootx64.efi /mnt/boot/EFI/boot/bootx64.efi.unsigned
        sbctl sign /mnt/boot/EFI/boot/bootx64.efi
        sbctl enroll-keys -m
        mkdir -p /mnt/usr/share/secureboot
        cp -rf /usr/share/secureboot/* /mnt/usr/share/secureboot/
    fi
}


upgrade_hosts() {
    if [ -d /mnt/home/$USERNAME/.local/tower ]; then
        # move tower configuration
        mkdir -p /home/$USERNAME/.local/
        cp -r /mnt/home/$USERNAME/.local/tower /home/$USERNAME/.local/
        cp -r /mnt/home/$USERNAME/.ssh /home/$USERNAME/
        chown -R $USERNAME:$USERNAME /home/$USERNAME/
        # ask confirmation to upgrade hosts
        runuser -u $USERNAME -- python $SCRIPT_DIR/askconfiguration.py end-upgrade
        if [ -f /tmp/upgradable-hosts ]; then
            # upgrade upgradable hosts
            runuser -u $USERNAME -- tower upgrade --hosts $(cat /tmp/upgradable-hosts)
            python $SCRIPT_DIR/askconfiguration.py end-hosts-upgrade
        fi
        if [ -d /mnt/home/$USERNAME/.local/tower/hosts/router ]; then
            if [ "$INSTALLED_PACKAGES" != "" ]; then
                # re-install thinclient package
                runuser -u $USERNAME -- tower install thinclient $INSTALLED_PACKAGES || true
            fi
        fi
        # move updated tower configuration back
        cp -r /mnt/home/$USERNAME/.local/tower /home/$USERNAME/.local/
        chown -R $USERNAME:$USERNAME /home/$USERNAME/
    else
        # no tower configuration found
        python $SCRIPT_DIR/askconfiguration.py end-install
    fi
}


install_thinclient() {
    # make sure /bin and /lib are executable
    chmod 755 /
    chmod 755 /bin
    chmod 755 /lib
    
    set_configuration
    prepare_drive
    update_live_system
    clone_live_system_to_disk
    install_bootloader
    install_secure_boot
    umount /mnt/boot
    if [ "$INSTALLATION_TYPE" == "upgrade" ]; then
        upgrade_hosts
    else
        python $SCRIPT_DIR/askconfiguration.py end-install
    fi
    unmount_and_reboot
}


unmount_and_reboot() {
    rm -f /mnt/crypto_keyfile.bin
    umount /mnt/home
    umount /mnt
    reboot
}


set_configuration() {
    SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"
    # initialize coniguration variables:
    # INSTALLATION_TYPE, ROOT_PASSWORD_HASH, USERNAME, PASSWORD_HASH,
    # LANG, TIMEZONE, KEYBOARD_LAYOUT, KEYBOARD_VARIANT,
    # TARGET_DRIVE, CRYPTKEY_DRIVE, SECURE_BOOT
    # STARTW_ON_LOGIN, DEFAULT_PACKAGES, ALPINE_BRANCH
    python $SCRIPT_DIR/askconfiguration.py
    source /root/tower.env
    if [ "$INSTALLATION_TYPE" == "upgrade" ]; then
        check_and_copy_key_from_boot_disk
        activate_root_disk
        set_config_from_root_partition
    fi
}

install_thinclient
