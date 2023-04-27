pkgname=tower-tools
pkgver=0.1.0
pkgrel=1
pkgdesc="Tower Tools"
url="https://github.com/towercomputers/tools"
arch="all"
src="./dist/*.whl"
depends="python3 py3-pip sudo openssh dhcpcd avahi avahi-tools wpa_supplicant rsync
         git iptables rsync lsblk perl-utils xz musl-locales e2fsprogs-extra
         nx-libs xsetroot mcookie"
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
