#!/bin/sh

set +x
set -e

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

# copy overlay prepared by buildthinclient.py
# cp -r ~/build-toweros-thinclient-work/overlay/* "$tmp"/

mkdir -p "$tmp"/etc/profile.d
cat <<EOF > "$tmp"/etc/profile.d/install.sh
apk --force-overwrite --quiet --progress add tower-cli
sh /var/towercomputers/installer/install-thinclient.sh
EOF
chmod +x "$tmp"/etc/profile.d/install.sh

# install services
rc_add devfs sysinit
rc_add dmesg sysinit
rc_add mdev sysinit
rc_add hwdrivers sysinit
rc_add modloop sysinit
rc_add hwclock boot
rc_add modules boot
rc_add sysctl boot
rc_add bootmisc boot
rc_add syslog-ng boot
rc_add mount-ro shutdown
rc_add killprocs shutdown
rc_add savecache shutdown

# generate apk overlay
tar -c -C "$tmp" ./ | gzip -9n > $HOSTNAME.apkovl.tar.gz
#cp $HOSTNAME.apkovl.tar.gz ~/