#!/bin/sh
# Alpine Linux genfstab

# default location for mounted root
SYSROOT=${SYSROOT:-/mnt}

in_list() {
	local i="$1"
	shift
	while [ $# -gt 0 ]; do
		[ "$i" = "$1" ] && return 0
		shift
	done
	return 1
}

fstype_is_pseudofs() {
  # list taken from util-linux source: libmount/src/utils.c
  pseudofs_types='anon_inodefs autofs bdev binfmt_misc cgroup configfs cpuset 
	debugfs devfs devpts devtmpfs dlmfs fuse.gvfs-fuse-daemon fusectl 
	hugetlbfs mqueue nfsd none pipefs proc pstore ramfs rootfs rpc_pipefs 
	securityfs sockfs spufs sysfs tmpfs efivarfs'
  in_list $1 $pseudofs_types
}

# wrapper to only show given device
_blkid() {
	blkid | grep "^$1:"
}

# if given device have an UUID display it, otherwise return the device
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

# generate an fstab from a given mountpoint. Convert to UUID if possible
enumerate_fstab() {
	local mnt="$1"
	local fs_spec= fs_file= fs_vfstype= fs_mntops= fs_freq= fs_passno=
	[ -z "$mnt" ] && return
	local escaped_mnt=$(echo $mnt | sed -e 's:/*$::' -e 's:/:\\/:g')
	awk "\$2 ~ /^$escaped_mnt(\/|\$)/ {print \$0}" /proc/mounts | \
		sed "s:$mnt:/:g; s: :\t:g" | sed -E 's:/+:/:g' | \
		while read fs_spec fs_file fs_vfstype fs_mntops fs_freq fs_passno; do
			if [ -z "$USE_PSEUDOFS" ] && fstype_is_pseudofs "$fs_vfstype"; then
				continue
			fi
			echo -e "$(uuid_or_device $fs_spec)\t${fs_file}\t${fs_vfstype}\t${fs_mntops} ${fs_freq} ${fs_passno}"
		done
	cat <<-__EOF__
		/dev/cdrom	/media/cdrom	iso9660	noauto,ro 0 0
		/dev/fd0	/media/floppy	vfat	noauto	0 0
		/dev/usbdisk	/media/usb	vfat	noauto	0 0
	__EOF__
}

usage() {
	cat <<-__EOF__
		usage: $0 [options] root

		options:
		 -h  Show this help
		 -P  Include printing mounts
		 -U  Use UUIDs for source identifiers

		genfstab generates output suitable for addition to an fstab file based on the
		devices mounted under the mountpoint specified by the given root.
	__EOF__
	exit 1
}

# Parse args
while getopts ":PU" opt; do
	case $opt in
		P) USE_PSEUDOFS=1;;
		U) USE_UUID=1;;
		*) usage;;
	esac
done
shift $(( $OPTIND - 1))

if [ -d "$1" ]; then
	SYSROOT=$1
fi

enumerate_fstab "$SYSROOT"

