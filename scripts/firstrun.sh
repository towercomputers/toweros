#!/bin/bash

set +e

/usr/lib/raspberrypi-sys-mods/imager_custom set_hostname '$NAME.tower'

/usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh -k '$PUBLIC_KEY'
/usr/lib/userconf-pi/userconf '$DEFAULT_SSH_USER' '$ENCRYPTED_PASSWORD'

SET_WLAN=$ONLINE
if $SET_WLAN; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_wlan '$WLAN_SSID' '$WLAN_PASSWORD' '$WLAN_COUNTRY'
fi

/usr/lib/raspberrypi-sys-mods/imager_custom set_keymap '$KEYMAP'
/usr/lib/raspberrypi-sys-mods/imager_custom set_timezone '$TIMEZONE'

mv -f /boot/dhcpcd.conf /etc/

rm -f /boot/firstrun.sh
sed -i 's| systemd.run.*||g' /boot/cmdline.txt
exit 0
