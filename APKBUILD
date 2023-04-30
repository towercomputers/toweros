pkgname=tower-tools
pkgver=0.1.0
pkgrel=1
pkgdesc="Tower Tools"
url="https://github.com/towercomputers/tools"
arch="all"
src="README.md ./docs/ ./dist/"
depends="coreutils python3 py3-pip py3-sh py3-rich
		sudo openssh dhcpcd avahi avahi-tools wpa_supplicant rsync
		git iptables rsync lsblk perl-utils xz musl-locales e2fsprogs-extra
		nx-libs xsetroot mcookie parted lsscsi figlet
		alpine-sdk build-base apk-tools acct acct-openrc alpine-conf sfdisk busybox fakeroot=1.31-r1 syslinux xorriso squashfs-tools
		mtools dosfstools grub-efi abuild agetty runuser"
makedepends="py3-gpep517 py3-pip py3-hatchling py3-wheel python3-dev"
license="none"

build() {
	rm -rf dist/
	pip install hatch
	~/.local/bin/hatch build -t wheel
	mkdir -p dist/pip-packages
	pip download -d dist/pip-packages dist/tower_tools*.whl
	mv dist/tower_tools*.whl dist/pip-packages

	cp -r scripts/toweros-thinclient/installer dist/
	
	mkdir -p dist/docs
	mv docs/* dist/docs/
	mv README.md dist/docs/
}

check() {
	return 0
}

package() {
	mkdir -p "$pkgdir"/var/cache
	cp -r dist/pip-packages "$pkgdir"/var/cache/

	cp -r dist/installer "$pkgdir"/var/towercomputers/

	mkdir -p "$pkgdir"/var/towercomputers
	cp -r dist/docs "$pkgdir"/var/towercomputers/
}
