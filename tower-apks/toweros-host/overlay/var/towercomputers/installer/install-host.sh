#!/bin/sh

set -e
set -x

update_passord() {
    REPLACE="$1:$2:"
    ESCAPED_REPLACE=$(printf '%s\n' "$REPLACE" | sed -e 's/[\/&]/\\&/g')
    sed -i "s/^$1:[^:]*:/$ESCAPED_REPLACE/g" /etc/shadow
}

check_and_copy_key_from_boot_disk() {
	if ! [ -f "$BOOT_MEDIA/crypto_keyfile.bin" ]; then
        echo "Key file not found in boot partition"
        exit 1
    fi
    key_is_ok=$(cryptsetup luksOpen --key-file $BOOT_MEDIA/crypto_keyfile.bin --test-passphrase $LVM_DISK && echo "OK" || echo "NOK")
    if [ "$key_is_ok" == "NOK" ]; then
        echo "Key file is not valid"
        exit 1
    fi
    cp $BOOT_MEDIA/crypto_keyfile.bin /crypto_keyfile.bin
    chmod 0400 /crypto_keyfile.bin
}

create_lvm_partitions() {
	# zeroing root drive
    dd if=/dev/zero of=$LVM_DISK bs=512 count=1 conv=notrunc
	# copy LUKS key from boot disk
	cp $BOOT_MEDIA/crypto_keyfile.bin /crypto_keyfile.bin
	chmod 0400 /crypto_keyfile.bin
	# create LUKS partition
	modprobe xchacha20
	modprobe adiantum
	modprobe nhpoly1305
	cryptsetup -q luksFormat -c xchacha12,aes-adiantum-plain64 $LVM_DISK /crypto_keyfile.bin
	cryptsetup luksAddKey $LVM_DISK /crypto_keyfile.bin --key-file=/crypto_keyfile.bin
	# initialize the LUKS partition
	cryptsetup luksOpen $LVM_DISK lvmcrypt --key-file=/crypto_keyfile.bin
	# create LVM physical volumes
	vgcreate -y vg0 /dev/mapper/lvmcrypt
	# create home volume
    lvcreate -l 20%FREE vg0 -n home
	# create root volume
    lvcreate -l 100%FREE vg0 -n root
    # set partition name
    ROOT_PARTITION="/dev/vg0/root"
	HOME_PARTITION="/dev/vg0/home"
}

activate_lvm_disk() {
    # initialize the LUKS partition
    cryptsetup luksOpen $LVM_DISK lvmcrypt --key-file=/crypto_keyfile.bin
    vgchange -ay vg0
    # set partitions names
    HOME_PARTITION="/dev/vg0/home"
    ROOT_PARTITION="/dev/vg0/root"
}

prepare_root_partition() {
	if [ "$INSTALLATION_TYPE" == "install" ]; then
		create_lvm_partitions
	else
		check_and_copy_key_from_boot_disk
		activate_lvm_disk
	fi
    # format partition
    mkfs.ext4 -F "$ROOT_PARTITION"
	# don't format home partition if we are updating the system
    if [ "$INSTALLATION_TYPE" == "install" ]; then
		mkfs.ext4 -F "$HOME_PARTITION"
	fi
	# create mount point
	mkdir -p /mnt
	# mount root partition
	mount $ROOT_PARTITION /mnt
	# mount home partition
	mkdir -p /mnt/home
	mount $HOME_PARTITION /mnt/home
	# copy LUKS key
	cp /crypto_keyfile.bin /mnt/crypto_keyfile.bin
}

prepare_home_directory() {
	# create first user
	adduser -D "$USERNAME" "$USERNAME"
	update_passord "$USERNAME" "$PASSWORD_HASH"
	# add user to doas config
	echo "permit nopass $USERNAME as root" > /etc/doas.conf
	# create home directory
	mkdir -p "/mnt/home/"
	# add publick key
	mkdir -p /mnt/home/$USERNAME/.ssh
	echo "$PUBLIC_KEY" > /mnt/home/$USERNAME/.ssh/authorized_keys
	chmod 700 /mnt/home/$USERNAME/.ssh
	chmod 600 /mnt/home/$USERNAME/.ssh/*
	# set shell prompt color
	echo "export PS1='\e[${COLOR}m[\\u@\\H \\W]\e[0m\\$ '" >> /mnt/home/$USERNAME/.profile
	# set XDG_RUNTIME_DIR and PS1
    cat <<EOF >> /mnt/home/$USERNAME/.profile
if [ -z "\$XDG_RUNTIME_DIR" ]; then
    XDG_RUNTIME_DIR="/tmp/\$(id -u)-runtime-dir"
	mkdir -pm 0700 "\$XDG_RUNTIME_DIR"
	export XDG_RUNTIME_DIR
fi
EOF
	chown -R "$USERNAME:$USERNAME" "/mnt/home/$USERNAME"
}

update_live_system() {
	# TODO: set locale
	setup-hostname -n $HOSTNAME
	setup-keymap $KEYBOARD_LAYOUT $KEYBOARD_VARIANT
	setup-timezone $TIMEZONE

	# change root password
	update_passord "root" "$PASSWORD_HASH"

	# configure firewall
	sh $SCRIPT_DIR/configure-firewall.sh "$THIN_CLIENT_IP" "$TOWER_NETWORK" "$HOSTNAME" "$ONLINE" "$ROUTER_IP"

	# configure default network
	cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
address $STATIC_HOST_IP/24
EOF

	# disable wireless devices
    rfkill block all || true

	# enable connection if requested
	if [ "$HOSTNAME" == "router" ]; then
		# enable wifi
		rfkill unblock wifi
		# setup wifi connection
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
		# enable services
		rc-update add wpa_supplicant boot
		# enable internet connection sharing
		cat <<EOF > /etc/sysctl.d/30-ipforward.conf
net.ipv4.ip_forward=1
net.ipv6.conf.default.forwarding=1
net.ipv6.conf.all.forwarding=1
EOF
		# Allow tcp forwarding for ssh tunneling (used by `install` and `run` commands)
		sed -i 's/AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config

		# randomize wlan0 mac address
		echo "macchanger -r wlan0" >> /etc/local.d/macchanger.start
		chmod +x /etc/local.d/macchanger.start
	else
		if [ "$ONLINE" == "true" ]; then
			# update network configuration
			echo "gateway $ROUTER_IP" >> /etc/network/interfaces
			# set DNS servers
			echo "nameserver 8.8.8.8" > /etc/resolv.conf
			echo "nameserver 8.8.4.4" >> /etc/resolv.conf
		fi
	fi
	
	# setup services
	rc-update add iptables default
	rc-update add dbus default
	rc-update add sshd default
	rc-update add networking boot
	if [ "$HOSTNAME" == "router" ] || [ "$ONLINE" == "true" ]; then
		rc-update add chronyd default
	fi
	if [ "$HOSTNAME" == "router" ]; then
		rc-update add tor default
	fi

	# update sshd configuration
	sed -i "s/#ListenAddress 0.0.0.0/ListenAddress $STATIC_HOST_IP/g" /etc/ssh/sshd_config
	sed -i "s/#PermitRootLogin prohibit-password/PermitRootLogin no/g" /etc/ssh/sshd_config
	sed -i "s/#PasswordAuthentication yes/PasswordAuthentication no/g" /etc/ssh/sshd_config
	sed -i "s/#KbdInteractiveAuthentication yes/KbdInteractiveAuthentication no/g" /etc/ssh/sshd_config
	sed -i "s/AllowTcpForwarding no/#AllowTcpForwarding no/g" /etc/ssh/sshd_config
	echo "rc_need=networking" >> /etc/conf.d/sshd

	# copy sshd host key from boot device
	mkdir -p /etc/ssh
	cp $BOOT_MEDIA/ssh_host_* /etc/ssh/
	chmod 600 /etc/ssh/ssh_host_*
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
    features="base mmc usb ext4 mmc vfat nvme vmd lvm cryptsetup cryptkey"
    echo "features=\"$features\"" > /mnt/etc/mkinitfs/mkinitfs.conf

    # apk reads config from target root so we need to copy the config
    mkdir -p /mnt/etc/apk/keys/
    cp /etc/apk/keys/* /mnt/etc/apk/keys/

    # init chroot
    mkdir -p /mnt/proc
    mount --bind /proc /mnt/proc
    mkdir -p /mnt/dev
    mount --bind /dev /mnt/dev

	mkdir -p /mnt/boot

    # install packages
    local apkflags="--initdb --quiet --progress --update-cache --clean-protected"
    local pkgs="$(grep -h -v -w sfdisk /mnt/etc/apk/world 2>/dev/null)"
    local repoflags="--repository $BOOT_MEDIA/apks"
    apk add --root /mnt $apkflags --overlay-from-stdin --force-overwrite $repoflags $pkgs <$ovlfiles

    # clean chroot
    umount /mnt/proc
    umount /mnt/dev

	# prepare boot and root partitions and folders
	mount -o remount,rw $BOOT_MEDIA
	cp -rf /mnt/boot/*rpi* $BOOT_MEDIA/boot/
	rm -Rf /mnt/boot

	# update fstab
	sed -i '/cdrom/d' /mnt/etc/fstab 
	sed -i '/floppy/d' /mnt/etc/fstab
	sed -i '/\/boot/d' /mnt/etc/fstab
	echo  "/dev/vg0/home /home ext4 rw,relatime 0 0" >> /mnt/etc/fstab

	# update cmdline.txt
	kernel_opts="quiet console=tty1 rootfstype=ext4 slab_nomerge init_on_alloc=1 init_on_free=1 page_alloc.shuffle=1 pti=on vsyscall=none debugfs=off oops=panic module.sig_enforce=1 lockdown=confidentiality mce=0 loglevel=0"
	kernel_opts="$kernel_opts root=$ROOT_PARTITION cryptroot=$LVM_DISK cryptkey=yes cryptdm=lvmcrypt"
    modules="loop,squashfs,sd-mod,usb-storage,vfat,ext4,nvme,vmd,kms,lvm,cryptsetup,cryptkey"
    cmdline="modules=$modules $kernel_opts"
    echo "$cmdline" > $BOOT_MEDIA/cmdline.txt

	# Get branch from buildhost.py
	# configure apk repositories if host is online
	if [ "$HOSTNAME" == "router" ] || [ "$ONLINE" == "true" ]; then
		mkdir -p /mnt/etc/apk
		cat <<EOF > /mnt/etc/apk/repositories 
http://dl-cdn.alpinelinux.org/alpine/$ALPINE_BRANCH/main
http://dl-cdn.alpinelinux.org/alpine/$ALPINE_BRANCH/community
#http://dl-cdn.alpinelinux.org/alpine/edge/testing
EOF
	fi

	# migrate from sudo to doas
	ln -s /usr/bin/doas /mnt/usr/bin/sudo || true
}

clean_and_reboot() {
	# disable auto installation on boot
	mv /mnt/etc/local.d/install-host.start /mnt/etc/local.d/install.bak || true
	# remove configuration file
	rm $BOOT_MEDIA/tower.env
	# remove sshd host keys
	rm $BOOT_MEDIA/ssh_host_*
	# remove keyfile
	rm /mnt/crypto_keyfile.bin
	# reboot
	reboot
}

init_configuration() {
	# tower.env MUST contains the following variables:
	# HOSTNAME, USERNAME, PUBLIC_KEY, PASSWORD_HASH, KEYBOARD_LAYOUT, KEYBOARD_VARIANT, 
	# TIMEZONE, LANG, ONLINE, WLAN_SSID, WLAN_SHARED_KEY, THIN_CLIENT_IP, TOWER_NETWORK, 
	# STATIC_HOST_IP, ROUTER_IP, INSTALLATION_TYPE, COLOR, ALPINE_BRANCH

	if [ -f /media/usb/tower.env ]; then # boot on usb
		source /media/usb/tower.env
		BOOT_MEDIA=/media/usb
		if [ -b /dev/mmcblk0 ]; then
			LVM_DISK=/dev/mmcblk0
		else
			BOOT_PART=$(df $BOOT_MEDIA | tail -1 | awk '{print $1}')
			if [ "$BOOT_PART" == "/dev/sda1" ]; then
				LVM_DISK=/dev/sdb
			else
				LVM_DISK=/dev/sda
			fi
		fi
	elif [ -f /media/mmcblk0p1/tower.env ]; then # boot on sdcard
		source /media/mmcblk0p1/tower.env
		BOOT_MEDIA=/media/mmcblk0p1
		if [ -b /dev/nvme0n1 ]; then
			LVM_DISK=/dev/nvme0n1
		else
			LVM_DISK=/dev/sda
		fi
	else
		echo "`tower.env` not found. Please ensure the root drive is not bootable, or try booting with the root drive removed for the first part of the boot sequence."
		exit 1
	fi

	SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"
}

install_host() {
	init_configuration
	prepare_root_partition
	prepare_home_directory
	update_live_system
	clone_live_system_to_disk
	clean_and_reboot
}

install_host
