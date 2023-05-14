#!/bin/sh -e

OVERLAY_PATH="$1"

cleanup() {
	rm -rf "$tmp"
}

rc_add() {
	mkdir -p "$tmp"/etc/runlevels/"$2"
	ln -sf /etc/init.d/"$1" "$tmp"/etc/runlevels/"$2"/"$1"
}

# cleanup on exit
tmp="$(mktemp -d)"
trap cleanup EXIT

# copy overlay prepared by buildhost.py
cp -r $OVERLAY_PATH/* "$tmp"/

# install services
rc_add devfs sysinit
rc_add dmesg sysinit
rc_add mdev sysinit
rc_add hwdrivers sysinit
rc_add modloop sysinit
rc_add modules boot
rc_add sysctl boot
rc_add bootmisc boot
rc_add syslog boot
rc_add klogd boot
rc_add mount-ro shutdown
rc_add killprocs shutdown
rc_add savecache shutdown
rc_add local default

# generate apk overlay
tar -c -C "$tmp" etc | gzip -9n > headless.apkovl.tar.gz
