#!/bin/bash

set -e
set -x

ROOT_PASSWORD=$1
USERNAME=$2
PASSWORD=$3

# change root password
usermod --password $(echo $ROOT_PASSWORD | openssl passwd -1 -stdin) root
# create first user
useradd -m $USERNAME -p $(echo $PASSWORD | openssl passwd -1 -stdin)
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
usermod -aG docker $USERNAME
groupadd netdev
usermod -aG netdev $USERNAME
echo 'export PATH=~/.local/bin:$PATH' >> /home/$USERNAME/.bash_profile
echo "exec startlxde" > /home/$USERNAME/.xinitrc