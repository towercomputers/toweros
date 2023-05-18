if [ -f /etc/profile.d/install.sh ]; then
    echo "Welcome to TowerOS-ThinClient Installer!" > /etc/issue
    echo "" >> /etc/issue
else
    echo "Welcome to TowerOS-ThinClient!" > /etc/issue
    echo "" >> /etc/issue

    if [ ! -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
        echo "Connect to internet with the following command:" >> /etc/issue
        echo "" >> /etc/issue
        echo "          setup-wifi <wifi-ssid> <wifi-password>" >> /etc/issue
        echo "" >> /etc/issue
    fi

    echo "Please see the ~/docs/README.md file to know how to get started with TowerOS-ThinClient." >> /etc/issue
    echo "" >> /etc/issue
fi