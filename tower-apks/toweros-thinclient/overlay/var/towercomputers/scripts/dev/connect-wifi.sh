#!/bin/bash

set -e
set -x

# set dns
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf

# set gateway (the `router` host)
sudo sed -i 's/#gateway /gateway /g' /etc/network/interfaces
sudo sed -i 's/#gateway /gateway /g' /etc/local.d/01_init_network.start

# restart network
sudo rc-service networking restart
