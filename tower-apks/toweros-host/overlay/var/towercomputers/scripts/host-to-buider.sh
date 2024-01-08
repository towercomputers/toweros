sudo apk add alpine-sdk xz rsync perl-utils musl-locales \
     py3-pip py3-requests py3-rich cairo cairo-dev python3-dev \
     gobject-introspection gobject-introspection-dev \
     xsetroot losetup squashfs-tools xorriso pigz mtools

sudo addgroup tower abuild
abuild-keygen -a -i

cd tower-lib
sudo pip install -e . --break-system-packages
cd ../tower-cli
sudo pip install -e . --break-system-packages --no-deps

# sudo sfdisk --delete /dev/sdb
# sudo parted --script /dev/sdb mklabel msdos
# sudo parted --script /dev/sdb mkpart primary fat32 0% 100%
# sudo mkdosfs -n bootfs -F 32 -s 4 -v /dev/sdb1
# sudo mount /dev/sdb1 MNT
# sudo tar -xpf toweros-thinclient-0.7.0-aarch64.tar.gz -C MNT/