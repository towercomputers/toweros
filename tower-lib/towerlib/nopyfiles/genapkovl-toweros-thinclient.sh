#!/bin/sh

set +x
set -e

cleanup() {
	rm -rf "$tmp"
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

if [ "$(arch)" == "aarch64" ]; then
    cat <<EOF > "$tmp"/etc/apk/world
alpine-base
raspberrypi-bootloader
linux-firmware-brcm
toweros-thinclient
EOF
else
    cat <<EOF > "$tmp"/etc/apk/world
alpine-base
syslinux
intel-media-driver
libva-intel-driver
linux-firmware
linux-firmware-none
toweros-thinclient
EOF
fi

rc_add() {
    mkdir -p "$tmp"/etc/runlevels/"$2"
    ln -sf /etc/init.d/"$1" "$tmp"/etc/runlevels/"$2"/"$1"
}

rc_add modloop sysinit

# generate apk overlay
if [ "$(arch)" == "aarch64" ]; then
    tar -c -C "$tmp" etc | gzip -9n > headless.apkovl.tar.gz
else
    tar -c -C "$tmp" ./ | gzip -9n > $HOSTNAME.apkovl.tar.gz
fi
