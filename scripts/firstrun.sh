#!/bin/bash

set +e

/usr/lib/raspberrypi-sys-mods/imager_custom set_hostname '$NAME.tower'

/usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh -k '$PUBLIC_KEY'
/usr/lib/userconf-pi/userconf '$USER' '$ENCRYPTED_PASSWORD'

SET_WLAN=$ONLINE
if $SET_WLAN; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_wlan '$WLAN_SSID' '$WLAN_PASSWORD' '$WLAN_COUNTRY'
fi

/usr/lib/raspberrypi-sys-mods/imager_custom set_keymap '$KEYMAP'
/usr/lib/raspberrypi-sys-mods/imager_custom set_timezone '$TIMEZONE'

mv -f /boot/dhcpcd.conf /etc/

tar -xf /boot/apt-offline-1.8.5.tar.gz --directory /tmp
cd /tmp/apt-offline
sudo python setup.py install
rm -rf /tmp/apt-offline /boot/apt-offline-1.8.5.tar.gz

sudo apt-offline install /boot/apt-update-20230207.zip > /firstrun.log
sudo apt-offline install /boot/x2goserver-apt.zip >> /firstrun.log
sudo apt-get -y install x2goserver x2goserver-xsession >> /firstrun.log
rm -f /boot/x2goserver-apt.zip /boot/apt-update-20230207.zip

rm -f /boot/firstrun.sh
sed -i 's| systemd.run.*||g' /boot/cmdline.txt
exit 0
