pkgname=tower-tools
pkgver=0.1.0
pkgrel=1
pkgdesc="Tower Tools"
url="https://github.com/towercomputers/tools"
arch="all"
src="./dist/*.whl"
depends="coreutils python3 py3-pip py3-rich py3-sh sudo openssh dhcpcd avahi avahi-tools wpa_supplicant rsync
         git iptables rsync lsblk perl-utils xz musl-locales e2fsprogs-extra
         nx-libs xsetroot mcookie parted
		 alpine-sdk build-base apk-tools alpine-conf busybox fakeroot syslinux xorriso squashfs-tools
		 mtools dosfstools grub-efi abuild"
makedepends="py3-gpep517 py3-hatchling py3-wheel python3-dev"
license="none"

build() {
	gpep517 build-wheel \
		--wheel-dir dist \
		--output-fd 3 3>&1 >&2
}

check() {
	return 0
}

package() {
	python3 -m installer -d "$pkgdir" \
		dist/*.whl
}
