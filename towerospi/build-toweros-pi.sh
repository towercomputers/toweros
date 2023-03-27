#!/bin/bash
# from https://github.com/RPi-Distro/pi-gen/blob/5d2c6f31cefc7710e3bbc44012b9ffb843294e34/export-image/prerun.sh

# sudo pacman -Sy bc parted qemu-user-static
# echo ':arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-arm-static:' > /proc/sys/fs/binfmt_misc/register

set -e
set -x

if [ $(id -u) -ne 0 ]; then
    echo "Please run with sudo"
    exit
fi

ARCHLINUXARM_TAR="ArchLinuxARM-rpi-armv7-latest.tar.gz"
NX_TAR="nx-armv7h.tar.gz"
IMG_FILE="toweros-pi.img"
WORKING_DIR="toweros-pi-work"
ROOTFS_DIR="$WORKING_DIR/ROOTFS"
EXPORT_ROOTFS_DIR="$WORKING_DIR/EXPORT_ROOTFS"

rm -f "$IMG_FILE"
rm -rf "$WORKING_DIR"

mkdir -p "$WORKING_DIR"
mkdir -p "$ROOTFS_DIR"
mkdir -p "$EXPORT_ROOTFS_DIR"

mkfs.ext4 -O ^has_journal,^resize_inode -E lazy_itable_init=0,root_owner=0:0 -m 0 -U clear -- "$WORKING_DIR/root.img" 4G
mount "$WORKING_DIR/root.img" "$EXPORT_ROOTFS_DIR"

if [ ! -f "$ARCHLINUXARM_TAR" ]; then
    wget http://os.archlinuxarm.org/os/$ARCHLINUXARM_TAR
fi

bsdtar -xpf $ARCHLINUXARM_TAR -C "$EXPORT_ROOTFS_DIR"
bsdtar -xpf $NX_TAR -C "$EXPORT_ROOTFS_DIR"
cp /usr/bin/qemu-arm-static "$EXPORT_ROOTFS_DIR/usr/bin"
cp install.sh "$EXPORT_ROOTFS_DIR"

# Compile NX
#cp makenx.sh "$EXPORT_ROOTFS_DIR"
#arch-chroot "$EXPORT_ROOTFS_DIR" /bin/sh /makenx.sh
#rm "$EXPORT_ROOTFS_DIR/makenx.sh"

arch-chroot "$EXPORT_ROOTFS_DIR" /bin/sh /install.sh

#rm "$EXPORT_ROOTFS_DIR/usr/bin/qemu-arm-static"
rm "$EXPORT_ROOTFS_DIR/install.sh"

sync "$EXPORT_ROOTFS_DIR"

BOOT_SIZE="$((256 * 1024 * 1024))"
ROOT_SIZE=$(du --apparent-size -s "$EXPORT_ROOTFS_DIR" --exclude boot --block-size=1 | cut -f 1)

# All partition sizes and starts will be aligned to this size
ALIGN="$((4 * 1024 * 1024))"
# Add this much space to the calculated file size. This allows for
# some overhead (since actual space usage is usually rounded up to the
# filesystem block size) and gives some free space on the resulting
# image.
ROOT_MARGIN="$(echo "($ROOT_SIZE * 0.2 + 200 * 1024 * 1024) / 1" | bc)"

BOOT_PART_START=$((ALIGN))
BOOT_PART_SIZE=$(((BOOT_SIZE + ALIGN - 1) / ALIGN * ALIGN))
ROOT_PART_START=$((BOOT_PART_START + BOOT_PART_SIZE))
ROOT_PART_SIZE=$(((ROOT_SIZE + ROOT_MARGIN + ALIGN  - 1) / ALIGN * ALIGN))
IMG_SIZE=$((BOOT_PART_START + BOOT_PART_SIZE + ROOT_PART_SIZE))

truncate -s "${IMG_SIZE}" "${IMG_FILE}"

parted --script "$IMG_FILE" mklabel msdos
parted --script "$IMG_FILE" unit B mkpart primary fat32 "$BOOT_PART_START" "$((BOOT_PART_START + BOOT_PART_SIZE - 1))"
parted --script "$IMG_FILE" unit B mkpart primary ext4 "$ROOT_PART_START" "$((ROOT_PART_START + ROOT_PART_SIZE - 1))"

echo "Creating loop device..."
cnt=0
until LOOP_DEV="$(losetup --show --find --partscan "$IMG_FILE")"; do
    if [ $cnt -lt 5 ]; then
        cnt=$((cnt + 1))
        echo "Error in losetup.  Retrying..."
        sleep 5
    else
        echo "ERROR: losetup failed; exiting"
        exit 1
    fi
done

BOOT_DEV="${LOOP_DEV}p1"
ROOT_DEV="${LOOP_DEV}p2"

mkdosfs -n bootfs -F 32 -s 4 -v "$BOOT_DEV" > /dev/null
mkfs.ext4 -L rootfs -O "^huge_file" "$ROOT_DEV" > /dev/null

mount -v "$ROOT_DEV" "$ROOTFS_DIR" -t ext4
mkdir -p "$ROOTFS_DIR/boot"
mount -v "$BOOT_DEV" "$ROOTFS_DIR/boot" -t vfat

rsync -aHAXx --exclude /boot "$EXPORT_ROOTFS_DIR/" "$ROOTFS_DIR/"
rsync -rtx "$EXPORT_ROOTFS_DIR/boot/" "$ROOTFS_DIR/boot/"

umount "$ROOTFS_DIR/boot"
umount "$ROOTFS_DIR"
umount "$EXPORT_ROOTFS_DIR"
losetup -D
rm -rf "$WORKING_DIR"
