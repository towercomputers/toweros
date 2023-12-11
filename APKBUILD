pkgname=tower-cli
pkgver=$(cat tower-lib/towerlib/__about__.py  | awk '{print $NF}' | sed 's/"//g')
pkgrel=0
pkgdesc="Tower CLI"
url="https://toweros.org/"
arch="x86_64"
license="Apache-2.0"
depends="python3 py3-pip py3-hatchling py3-wheel py3-requests py3-passlib py3-rich"
makedepends="py3-gpep517 py3-hatchling py3-wheel python3-dev"
# no apk for these
pipdepends="sh==1.14.3 shtab==1.6.5 sshconf==0.2.5 yaspin==2.3.0 argparse-manpage==4.5 backports.pbkdf2==0.1"

build() {
	cd tower-lib
    hatch build -t wheel
    cd ../tower-cli
    hatch build -t wheel
    cd ..
    cp tower-lib/dist/tower_lib-$pkgver-py3-none-any.whl $srcdir
    cp tower-cli/dist/tower_cli-$pkgver-py3-none-any.whl $srcdir
    pip download $pipdepends -d $srcdir
}

check() {
    return 0
}

package() {
    for pk in $(ls $srcdir/*.whl); do
        echo "Installing: $pk"
        python3 -m installer -d "$pkgdir" $pk
    done
    # old packages
    pip3 install --target="$pkgdir/usr/lib/python3.11/site-packages/" --find-links="$srcdir" \
                --use-pep517 --no-warn-script-location --no-deps --ignore-requires-python --no-cache-dir \
                --use-deprecated=legacy-resolver --upgrade --root-user-action=ignore \
                argparse-manpage==4.5 backports.pbkdf2==0.1
    mv $pkgdir/usr/lib/python3.11/site-packages/bin/* $pkgdir/usr/bin/
}