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

profile_tower() {
	profile_base
	profile_abbrev="tower"
	title="TowerOS-ThinClient"
	desc="Towercomputer distribution for Thin Client."
	image_ext="iso"
	output_format="iso"
	arch="x86 x86_64"
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

