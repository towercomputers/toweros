pkgname=tower-cli
pkgver=$(cat tower-lib/towerlib/__about__.py  | awk '{print $NF}' | sed 's/"//g')
pkgrel=0
pkgdesc="Tower CLI"
url="https://toweros.org/"
arch="x86_64"
license="Apache-2.0"
depends=$(cat tower-lib/toweros-installers/toweros-thinclient/world | tr '\n' ' ')
makedepends="py3-gpep517 python3-dev py3-hatchling py3-wheel"
# no apk for these
pipdepends="sh==2.0.6 shtab==1.6.5 sshconf==0.2.5 yaspin==3.0.1 \
            argparse-manpage==4.5 backports.pbkdf2==0.1"

build() {
    # build tower-lib and tower-cli
	cd tower-lib
    hatchling build -t wheel
    cd ../tower-cli
    hatchling build -t wheel
    cd ..
    # put built packages in srcdir
    cp tower-lib/dist/tower_lib-$pkgver-py3-none-any.whl $srcdir
    cp tower-cli/dist/tower_cli-$pkgver-py3-none-any.whl $srcdir
    # download dependencies in srcdir
    pip download $pipdepends -d $srcdir
    # copy overlay files in srcdir
    cp -r tower-lib/toweros-installers/toweros-thinclient/overlay $srcdir/
    # build toweros-host image
    cd tower-build-cli
    ./tower-build host --build-dir $srcdir
    cd ..
    # copy documentation
    cp -r docs/src $srcdir/docs
    argparse-manpage --pyfile tower-cli/towercli/tower.py \
        --function towercli_parser \
        --author TowerOS \
        --project-name TowerOS \
        --url 'https://toweros.org' \
        --prog tower \
        --manual-title 'Tower CLI Manual' \
        --output $srcdir/tower.1
}

check() {
    return 0
}

package() {
    # wheel packages
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
    # install overlay files
    cp -r $srcdir/overlay/* $pkgdir/
    # install host images
    mkdir -p $pkgdir/var/towercomputers/builds
    cp $srcdir/*.xz $pkgdir/var/towercomputers/builds/
    # install docs
    cp -r $srcdir/docs $pkgdir/var/towercomputers/
    mkdir -p $pkgdir/usr/share/man/man1
    cp $srcdir/tower.1 $pkgdir/usr/share/man/man1/
}