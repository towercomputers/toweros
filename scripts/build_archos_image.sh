sudo pacman -S archiso
sudo pacman -Sy archlinux-keyring
sudo pacman -Su

mkdir /tmp/blankdb
#pacman -S - < pkglist.txt
sudo pacman -Syw --cachedir ./root/towerpackages --dbpath /tmp/blankdb --noconfirm \
    base linux linux-firmware \
    iwd openssh sudo grub efibootmgr \
    dhcpcd git python python-pip avahi \
    iw wireless_tools base-devel docker \
    lxde xorg-xinit nano vi

git clone https://aur.archlinux.org/nx.git && cd nx && makepkg -c -s -r --noconfirm && cd ..

sudo pacman -Uw --cachedir ./root/towerpackages --dbpath /tmp/blankdb --noconfirm nx/*.zst

sudo repo-add ./root/towerpackages/towerpackages.db.tar.gz ./root/towerpackages/*[^sig]

cp -r /usr/share/archiso/configs/releng/ archtower
cp root/*.sh archtower/airootfs/root/
cp root/pacman.conf archtower/airootfs/root/
sudo mv root/towerpackages archtower/airootfs/root/

sudo mkarchiso -v archtower/

rm -rf archtower/ root/towerpackages nx/ work/