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

# launch installer on login
mkdir -p "$tmp"/etc/profile.d
cat <<EOF > "$tmp"/etc/profile.d/install.sh
#!/bin/sh
sh /var/towercomputers/installer/install-thinclient.sh
EOF
chmod +x "$tmp"/etc/profile.d/install.sh

# auto-login
cat <<EOF > "$tmp"/etc/inittab
# /etc/inittab
::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default
# Set up a couple of getty's
tty1::respawn:/sbin/agetty --skip-login --nonewline --noissue --autologin root --noclear 38400 tty1
tty2::respawn:/sbin/getty 38400 tty2
tty3::respawn:/sbin/getty 38400 tty3
tty4::respawn:/sbin/getty 38400 tty4
tty5::respawn:/sbin/getty 38400 tty5
tty6::respawn:/sbin/getty 38400 tty6
# Stuff to do for the 3-finger salute
::ctrlaltdel:/sbin/reboot
# Stuff to do before rebooting
::shutdown:/sbin/openrc shutdown
EOF

mkdir -p "$tmp"/etc/apk
cat <<EOF > "$tmp"/etc/apk/world
alpine-base
toweros-thinclient
EOF

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
