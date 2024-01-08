set -x

profile_tower() {
    profile_base
    profile_abbrev="tower"
    title="TowerOS"
    desc="TowerOS for thin clients."
    image_ext="tar.gz"

    arch="aarch64"
    kernel_flavors="rpi"
    kernel_cmdline="console=tty1"
    initfs_features="base squashfs mmc usb kms dhcp https"
    grub_mod=
    hostname="rpi"
    
    apkovl="aports/scripts/genapkovl-toweros-thinclient.sh"
    local _k _a
    for _k in $kernel_flavors; do
        apks="$apks linux-$_k"
        for _a in $kernel_addons; do
            apks="$apks $_a-$_k"
        done
    done
    apks="$apks raspberrypi-bootloader linux-firmware-brcm toweros-thinclient"
}

