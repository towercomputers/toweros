sudo pacman -Suy
sudo pacman -S archiso

mkdir /tmp/blankdb
#pacman -S - < pkglist.txt
sudo pacman -Syw --cachedir ./root/towerpackages --dbpath /tmp/blankdb --noconfirm \
    base linux linux-firmware \
    iwd openssh sudo grub efibootmgr \
    dhcpcd git python python-pip avahi \
    iw wireless_tools base-devel docker \
    archiso lxde xorg-xinit nano vi

git clone https://aur.archlinux.org/nx.git && cd nx && makepkg -c -s -r --noconfirm && cd ..

sudo pacman -Uw --cachedir ./root/towerpackages --dbpath /tmp/blankdb --noconfirm nx/*.zst
sudo cp nx/*.zst root/towerpackages/

sudo repo-add ./root/towerpackages/towerpackages.db.tar.gz ./root/towerpackages/*[^sig]

pip download "tower-tools @ git+ssh://github.com/towercomputing/tools.git@archos" -d root/pippackages/

cp -r /usr/share/archiso/configs/releng/ archtower
sudo cp -r root/* archtower/airootfs/root/

sudo mkarchiso -v archtower/

#sudo cat out/*.iso | sudo tee /dev/sdb > /dev/null

rm -rf archtower/ root/towerpackages root/pippackages/ nx/ work/
