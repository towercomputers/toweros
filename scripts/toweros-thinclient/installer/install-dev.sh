#!/bin/bash
#
# The purpose of this script is to finish the installation for a development environment. 
# It performs the following actions:
#       - connects to the internet
#       - configure git and download tower-tools sources from Github
#       - possibly opens an ssh access
#       - install hatch
# Typically this script is called from a one line script located on a USB key which also contains
# the private key for Github. For example:
# 
# $ sudo mount --mkdir /dev/sdb1 SD
# $ ls SD/
# finish.sh id_ed25519
# $ cat finish.sh
# sh ~/install_dev.sh mywifibox mywifipassord \
#    "Ouziel Slama" ouziel@gmail.com ~/SD/id_ed25519 \
#    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJMdPXjBDbI7fV4ieSkT9GJZghyXtcmuS1oiI6qLils2 air"
#

set -e
set -x

WIFI_SSID="$1"
WIFI_PASSWORD="$2"
GIT_NAME="$3"
GIT_EMAIL="$4"
GIT_KEY_PATH="$5"
# set this variable if you need to connect with ssh from another host
AUTHORIZED_KEY="$6"

CONNECTED=false

if [ ! -z "$WIFI_SSID" ]; then
    sudo wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" | sudo tee /etc/wpa_supplicant/wpa_supplicant.conf
    sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
    sudo udhcpc -i wlan0
    echo "waiting connection..."
    set +x
    until ping -c1 www.google.com >/dev/null 2>&1; do :; done
    set -x
    CONNECTED=true
    echo "http://dl-cdn.alpinelinux.org/alpine/edge/main" | sudo tee /etc/apk/repositories
    echo "http://dl-cdn.alpinelinux.org/alpine/edge/community" | sudo tee -a /etc/apk/repositories
    echo "http://dl-cdn.alpinelinux.org/alpine/edge/testing" | sudo tee -a /etc/apk/repositories
fi

if [ ! -z "$GIT_NAME" ]; then
    git config --global user.email "$GIT_NAME"
fi

if [ ! -z "$GIT_EMAIL" ]; then
    git config --global user.name "$GIT_EMAIL"
fi

if [ ! -z "$GIT_KEY_PATH" ]; then
    mkdir -p ~/.ssh
    cp $GIT_KEY_PATH ~/.ssh
    KEY_NAME=$(basename $GIT_KEY_PATH)
    touch ~/.ssh/config
    echo "Host github.com" >> ~/.ssh/config
    echo "  HostName github.com" >> ~/.ssh/config
    echo "  IdentityFile ~/.ssh/$KEY_NAME" >> ~/.ssh/config
    echo "  User git" >> ~/.ssh/config
    GITHUB_KEY="github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk="
    touch ~/.ssh/known_hosts
    echo "$GITHUB_KEY" >> ~/.ssh/known_hosts
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/*
    if $CONNECTED; then
        mkdir -p ~/towercomputers
        cd ~/towercomputers
        git clone git@github.com:towercomputers/tools.git
    fi
fi

if $CONNECTED; then
    pip install hatch
fi

if [ ! -z "$AUTHORIZED_KEY" ]; then
    sudo iptables -A TCP -p tcp --dport 22 -j ACCEPT
    sudo iptables -D INPUT -j REJECT --reject-with icmp-proto-unreachable
    sudo iptables -A INPUT -j REJECT --reject-with icmp-proto-unreachable
    sudo /etc/init.d/iptables save
    sudo rc-update add sshd default
    sudo rc-service sshd start
    mkdir -p ~/.ssh
    touch ~/.ssh/authorized_keys
    echo "$AUTHORIZED_KEY" > ~/.ssh/authorized_keys
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/*
fi
