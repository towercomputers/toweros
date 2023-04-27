make_tower(){
	#if necessary abuild-keygen -a
	abuild checksum
	abuild -r

	cp tools/scripts/toweros-thinclient/mkimg.tower.sh aports/scripts/
	cp tools/scripts/toweros-thinclient/genapkovl-tower.sh aports/scripts/

sh aports/scripts/mkimage.sh \
	--outdir ~/ \
	--arch x86_64 \
	--repository http://mirrors.ircam.fr/pub/alpine/edge/main \
	--repository http://mirrors.ircam.fr/pub/alpine/edge/community \
	--repository http://mirrors.ircam.fr/pub/alpine/edge/testing \
	--repository file:///home/tower/packages/towercomputers \
	--profile tower \
	--tag v0.0.1
}

profile_standard() {
	title="Standard"
	desc="Alpine as it was intended.
		Just enough to get you started.
		Network connection is required."
	profile_base
	profile_abbrev="std"
	image_ext="iso"
	arch="aarch64 armv7 x86 x86_64 ppc64le riscv64 s390x"
	output_format="iso"
	kernel_addons="xtables-addons"
	case "$ARCH" in
	s390x)
		apks="$apks s390-tools"
		initfs_features="$initfs_features dasd_mod qeth zfcp"
		initfs_cmdline="modules=loop,squashfs,dasd_mod,qeth,zfcp quiet"
		;;
	ppc64le)
		initfs_cmdline="modules=loop,squashfs,sd-mod,usb-storage,ibmvscsi quiet"
		;;
	riscv64)
		kernel_flavors="edge"
		kernel_cmdline="console=tty0 console=ttyS0,115200 console=ttySIF0,115200"
		kernel_addons=
		;;
	esac
}


profile_tower() {
	profile_standard
	profile_abbrev="tower"
	title="TowerOS-ThinClient"
	desc="Towercomputer distribution for Thin Client."
	arch="x86 x86_64"
	kernel_addons="xtables-addons zfs"
	boot_addons="amd-ucode intel-ucode"
	initrd_ucode="/boot/amd-ucode.img /boot/intel-ucode.img"
	apkovl="aports/scripts/genapkovl-tower.sh"
	apks="$apks tower-tools nano vim net-tools"
	local _k _a
	for _k in $kernel_flavors; do
		apks="$apks linux-$_k"
		for _a in $kernel_addons; do
			apks="$apks $_a-$_k"
		done
	done
	apks="$apks linux-firmware linux-firmware-none"
}

