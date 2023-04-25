#!/bin/bash

set -e
set -x


ROOT_PASSWORD=$1
USERNAME=$2
PASSWORD=$3
LANG=$4
TIMEZONE=$5
KEYBOARD_LAYOUT=$6
KEYBOARD_VARIANT=$7
TARGET_DRIVE=$8

# change root password
echo -e "$ROOT_PASSWORD\n$ROOT_PASSWORD" | passwd root
# create first user
adduser -D "$USERNAME" "$USERNAME"
echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME"

setup-timezone "$TIMEZONE"
setup-keymap "$KEYBOARD_LAYOUT" "$KEYBOARD_VARIANT"
setup-hostname -n tower

apk add wpa_supplicant
yes | setup-disk -m sys "$TARGET_DRIVE"

# on first boot as root
# ip link set wlan0 up
# wpa_passphrase 'ExampleWifiSSID' 'ExampleWifiPassword' > /etc/wpa_supplicant/wpa_supplicant.conf
# wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
# udhcpc -i wlan0
# setup-apkrepos
# apk update
# uncomment community repo in /etc/apk/repositories
# apk add sudo
# echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
# exit and login as tower