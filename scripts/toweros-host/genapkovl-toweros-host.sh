#!/bin/sh -e

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
e2fsprogs
sfdisk
avahi
avahi-tools
iptables
sudo
dhcpcd
openssh
xauth
nano
EOF


mkdir -p "$tmp"/etc/apk/keys
makefile root:root 0644 "$tmp"/etc/apk/keys/ouziel@gmail.com-644fe6fa.rsa.pub <<EOF
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAzpymy4D9WP1OQB6TZ+/s
T4QY0skhEa7qlnbbke/UwuUxxlvU6CwBvzmba82m02ThTiuHB0G5GisQgWNriI8G
axCC0amzqtpL2fyC6dDK92ZuYtZa6wKVck4iNiZxcFAM3hp2or0hLSkck7Viax4b
ltwoeRTGdrMac+1B3uq8vw3flWpraXoTXkF659WMLBs50YRZy2khr6pxL1Rr18ge
RGhNOZ8wHXQbRCPWBtLmZrZ+VuOBCM4mVOQa+v3Xw5wm7vs0SrvCcJnvZ42JQkEr
RHOT8aU8eadmPNp2eKPvyDZotG8BBBhG99QOOeUAsDWcwlNPNdt+bw+uM3A6VPPB
t2zCYcqOFr69YaMFsGNCzx9e+Nn3CK1934KrZnIKRFUCw52QNxoBdkkVWYq2Go/d
+TGRuJ9U3a/p8cq/mV3L85YBRw+2XYAL6aN+5Vfg+UrOjCZRbPSN3zfpgTzysjuh
VrnFwse5+Fz6o6/t5oYGxNuT7MftuIbsU9RpEdauiU5osTbRJjD+/IQHzgLCmU7K
fCaw81DrznLXz59kBboSHvhsMaQeBUFCOW6DzXS4vNdHjcceYLnvnA+5TyTunPIq
akWJ9YHOVd/4CpAl5GgjPoucXsoW4hEhGU9P/UYwVVF4t2GWA0nm/s8XH9kljnT2
sabyotq5pg08FDFLRmYcsfsCAwEAAQ==
-----END PUBLIC KEY-----
EOF

# welcome messages
makefile root:root 0644 "$tmp"/etc/issue <<EOF
Welcome to TowerOS-ThinClient Installer!
EOF
touch "$tmp"/etc/motd

# auto-start installer
mkdir -p "$tmp"/etc/local.d/
makefile root:root 0755 "$tmp"/etc/local.d/install.sh <<EOF
#!/bin/sh

echo 'INSTALL'
#apk add nx-libs dosfstools e2fsprogs sfdisk avahi avahi-tools \
#	iptables sudo dhcpcd openssh xauth
EOF

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

# install services
rc_add local default
rc_add devfs sysinit
rc_add dmesg sysinit
rc_add mdev sysinit
rc_add hwdrivers sysinit
rc_add modloop sysinit
rc_add hwclock boot
rc_add modules boot
rc_add sysctl boot
rc_add bootmisc boot
rc_add syslog boot
rc_add mount-ro shutdown
rc_add killprocs shutdown
rc_add savecache shutdown

# generate apk overlay
tar -c -C "$tmp" etc | gzip -9n > headless.apkovl.tar.gz
