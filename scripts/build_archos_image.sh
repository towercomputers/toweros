sudo pacman -S archiso
cp -r /usr/share/archiso/configs/releng/ archtower
cp *.sh archtower/airootfs/root/
sudo 
mkarchiso -v archtower/