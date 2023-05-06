profile_tower() {
	profile_base
	profile_abbrev="tower"
	title="TowerOS-ThinClient"
	desc="Towercomputer distribution for Thin Client."
	image_ext="iso"
	output_format="iso"
	arch="x86 x86_64"
	kernel_addons="xtables-addons zfs"
	boot_addons="amd-ucode intel-ucode"
	initrd_ucode="/boot/amd-ucode.img /boot/intel-ucode.img"
	apkovl="aports/scripts/genapkovl-tower-thinclient.sh"
	apks="$apks coreutils python3 py3-pip py3-rich
		sudo openssh dhcpcd avahi avahi-tools wpa_supplicant rsync
		git iptables rsync lsblk perl-utils xz musl-locales e2fsprogs-extra
		nx-libs xsetroot mcookie parted lsscsi figlet
		alpine-sdk build-base apk-tools acct acct-openrc alpine-conf sfdisk busybox 
		fakeroot syslinux xorriso squashfs-tools
		mtools dosfstools grub-efi abuild agetty runuser
		nano vim net-tools losetup"
	local _k _a
	for _k in $kernel_flavors; do
		apks="$apks linux-$_k"
		for _a in $kernel_addons; do
			apks="$apks $_a-$_k"
		done
	done
	apks="$apks linux-firmware linux-firmware-none"
}

