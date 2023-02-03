#!/bin/bash

set +e

/usr/lib/raspberrypi-sys-mods/imager_custom set_hostname $HOSTNAME
/usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh -k '$PUBLIC_KEY'
/usr/lib/userconf-pi/userconf '$LOGIN' '$PASSWORD'
/usr/lib/raspberrypi-sys-mods/imager_custom set_keymap '$KEY_MAP'
/usr/lib/raspberrypi-sys-mods/imager_custom set_timezone '$TIME_ZONE'

mv -f /boot/dhcpcd.conf /etc/
rm -f /boot/firstrun.sh
sed -i 's| systemd.run.*||g' /boot/cmdline.txt
exit 0
