#!/bin/bash

set +e
set -x

if [ -f "/boot/tower.env" ]; then
    . "/boot/tower.env"

    /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname "$NAME.tower"
    /usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh -k "$PUBLIC_KEY"
    /usr/lib/userconf-pi/userconf "$USER" "$ENCRYPTED_PASSWORD"
    /usr/lib/raspberrypi-sys-mods/imager_custom set_keymap "$KEYMAP"
    /usr/lib/raspberrypi-sys-mods/imager_custom set_timezone "$TIMEZONE"

    if "$ONLINE" == "true"; then
        /usr/lib/raspberrypi-sys-mods/imager_custom set_wlan "$WLAN_SSID" "$WLAN_PASSWORD" "$WLAN_COUNTRY"
    fi

    sudo sh /boot/configure_firewall.sh "$THIN_CLIENT_IP" "$TOWER_NETWORK"

    rm -f /boot/tower.env
fi

rm -f /boot/firstrun.sh
sed -i 's| systemd.run.*||g' /boot/cmdline.txt
exit 0
