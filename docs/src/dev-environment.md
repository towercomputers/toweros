## Set Up Development Environment

### Connect to internet

To connect the thin client to the Internet you must:

1. Provision a `router`.
1. Set the gateway on the thin client to `192.168.2.1` (the router's IP address):

    The file `/etc/network/interfaces` must contain the following:

        auto lo
        iface lo inet loopback
        auto eth0
        iface eth0 inet static
            address 192.168.2.100/24
            gateway 192.168.2.1
        auto eth1
        iface eth1 inet static
            address 192.168.3.100/24

1. Set the DNS server on the thin client:

    The file `/etc/resolv.conf` must contain the following:

        nameserver 8.8.8.8
        nameserver 8.8.4.4

1. Restart the network with: `[thinclient]$ sudo rc-service networking restart`

### Configure Git and download Github repository

Configure `git`, download Github repository in `~/towercomputers/toweros` and install `hatch` with:

```
[thinclient]$ /var/towercomputers/install-dev.sh <git-name> <git-email> <git-private-key-path>
```

### Use `tower-cli` with `hatch`

```
[thinclient]$ cd ~/towercomputers/toweros/tower-cli
[thinclient]$ hatch run tower --help
```
