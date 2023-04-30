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
	apkovl="aports/scripts/genapkovl-tower.sh"
	apks="$apks toweros-thinclient-installer"
	local _k _a
	for _k in $kernel_flavors; do
		apks="$apks linux-$_k"
		for _a in $kernel_addons; do
			apks="$apks $_a-$_k"
		done
	done
	apks="$apks linux-firmware linux-firmware-none"
}

