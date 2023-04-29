pkgname=tower-tools
pkgver=0.1.0
pkgrel=1
pkgdesc="Tower Tools"
url="https://github.com/towercomputers/tools"
arch="all"
src="./dist/*.whl"
depends="coreutils python3 py3-pip py3-rich py3-sh py3-requests py3-hatchling py3-wheel py3-setuptools
		sudo openssh dhcpcd avahi avahi-tools wpa_supplicant rsync
		git iptables rsync lsblk perl-utils xz musl-locales e2fsprogs-extra
		nx-libs xsetroot mcookie parted lsscsi figlet
		alpine-sdk build-base apk-tools alpine-conf sfdisk busybox fakeroot=1.31-r1 syslinux xorriso squashfs-tools
		mtools dosfstools grub-efi abuild agetty"
makedepends="py3-gpep517 py3-hatchling py3-wheel python3-dev py3-pip"
license="none"

build() {
	rm -r dist/*.whl || true
	gpep517 build-wheel --wheel-dir dist --output-fd 3 3>&1 >&2
	pip download -d dist dist/tower_tools*.whl
}

check() {
	return 0
}

package() {
	pip install --no-index --find-links=dist/ -t "$pkgdir" tower-tools
}
