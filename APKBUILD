pkgname=tower-tools
pkgver=0.1.0
pkgrel=1
pkgdesc="Tower Tools"
url="https://github.com/towercomputers/tools"
arch="all"
src="./dist/"
depends="coreutils python3 py3-pip
		sudo openssh dhcpcd avahi avahi-tools wpa_supplicant rsync
		git iptables rsync lsblk perl-utils xz musl-locales e2fsprogs-extra
		nx-libs xsetroot mcookie parted lsscsi figlet
		alpine-sdk build-base apk-tools alpine-conf sfdisk busybox fakeroot=1.31-r1 syslinux xorriso squashfs-tools
		mtools dosfstools grub-efi abuild agetty"
makedepends="py3-gpep517 py3-pip py3-hatchling py3-wheel python3-dev"
license="none"

build() {
	rm -rf dist/
	gpep517 build-wheel \
		--wheel-dir dist \
		--output-fd 3 3>&1 >&2
	mkdir -p dist/cache
	pip download -d dist/cache dist/tower_tools*.whl
}

check() {
	return 0
}

package() {
	mkdir -p ~/pip-cache
	cp dist/cache/* ~/pip-cache/
	python3 -m installer -d "$pkgdir" dist/*.whl
}
