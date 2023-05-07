#!/bin/sh -e

SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

cleanup() {
	rm -rf "$tmp"
}

makefile() {
	OWNER="$1"
	PERMS="$2"
	FILENAME="$3"
	cat > "$FILENAME"
	chown "$OWNER" "$FILENAME"
	chmod "$PERMS" "$FILENAME"
}

rc_add() {
	mkdir -p "$tmp"/etc/runlevels/"$2"
	ln -sf /etc/init.d/"$1" "$tmp"/etc/runlevels/"$2"/"$1"
}

# cleanup on exit
tmp="$(mktemp -d)"
trap cleanup EXIT

# install toweros-thinclient-installer
mkdir -p "$tmp"/etc/apk
makefile root:root 0644 "$tmp"/etc/apk/world <<EOF
alpine-base
openssl
nx-libs
dosfstools
e2fsprogs=1.47.0-r2
e2fsprogs-extra=1.47.0-r2
sfdisk
avahi
avahi-tools
iptables
sudo
dhcpcd
openssh
xauth
nano
kbd-bkeymaps
parted
lsblk
tzdata
wpa_supplicant
dbus
EOF

mkdir -p "$tmp"/etc/apk/keys
makefile root:root 0644 "$tmp"/etc/apk/keys/ouziel@gmail.com-644fe6fa.rsa.pub <<EOF
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAwU4VzQTet4EVb3MiBnI3
srkJCQ/WrhdyhLJ/9b4f3XVAdfDc2FfojFTxvR/w++/sTVqSdeCIYXMqecvR2pVV
wsLqaYBYjCgSzqHhUm+alcAcunLGDYYGIxaIbBZHx9roobtpqNi0bE9Rl7kWEaBb
/6U+kzcjGBrmCjLUF48SEeX5nhDCWXmt6fkyivRHVyLtLrGqcahXw7LhNwh5DDOp
MLZ6XZoPwozZU+dmZOnupmL4kzVOqfPbqDdhHLzNXFYzqIL8Cp082I5wogPkqxtY
S9j8HQi16/4jmD6ZB9j6BsqjdAsoEROpgyq0B4/tl+1pipq/LfF2MvhoOFK1kmg3
GzDHE7mjeAq3oSCJ3w0jPZxQU8N7Ur236PJ973gNJREF0xPARk/ViZlvXyWX/kpm
omqihF/ZultGnGKQ8OMwaBvWjXdJOc2saJgxjn35BOKc8UlWSc4Fjm+fPvo/ujm+
ML1yjcbx2kf2VxqqINhMeh0744AIHp7E8GYMjno13L0OUbuOPb56YRudJEdnm5pj
SapVasGUp+8ussbL10bopvGGwJEe5NaAOIxT8WS4eq1q+Cw3P1mJ5c+b97gVp7t+
yuXkp+m7llw24KzCZMo+y6/C69N/vz82Pz/lA5VWP+Fxx/jC6sCpe7NVd+UJteZ1
cR0AMpwKS+pQED64plhXXqkCAwEAAQ==
-----END PUBLIC KEY-----
EOF

# welcome messages
makefile root:root 0644 "$tmp"/etc/issue <<EOF
Welcome to TowerOS-Host!
EOF
touch "$tmp"/etc/motd

# auto-start installer
mkdir -p "$tmp"/etc/local.d/
cat $SCRIPT_DIR/install-host.sh | makefile root:root 0755 "$tmp"/etc/local.d/install.start
#cat $SCRIPT_DIR/install-host.sh | makefile root:root 0755 "$tmp"/etc/local.d/install.sh
cat $SCRIPT_DIR/configure-firewall.sh | makefile root:root 0755 "$tmp"/etc/local.d/configure-firewall.sh

# set auto-login
makefile root:root 0644 "$tmp"/etc/inittab <<EOF
# /etc/inittab

::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default

# Set up a couple of getty's
tty1::respawn:/sbin/getty 38400 tty1
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

mkdir -p "$tmp"/etc/network
makefile root:root 0644 "$tmp"/etc/network/interfaces <<EOF
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
EOF

# install services
rc_add devfs sysinit
rc_add dmesg sysinit
rc_add mdev sysinit
rc_add hwdrivers sysinit
rc_add modloop sysinit

#rc_add hwclock boot
rc_add modules boot
rc_add sysctl boot
rc_add bootmisc boot
rc_add syslog boot

rc_add mount-ro shutdown
rc_add killprocs shutdown
rc_add savecache shutdown

rc_add local default
rc_add dhcpcd default
rc_add dbus default
rc_add avahi-daemon default
rc_add iptables default
rc_add sshd default
rc_add wpa_supplicant boot
rc_add networking boot

# generate apk overlay
tar -c -C "$tmp" etc | gzip -9n > headless.apkovl.tar.gz
