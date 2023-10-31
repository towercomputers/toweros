# Development Guide

## 1. Setup environement

To connect to internet you must:

1. provision a `router`
2. set the thinclient gateway to `192.168.2.1` (the router`s ip):

The file /etc/network/interfaces must contain the following:

```
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
    address 192.168.2.100/24
    gateway 192.168.2.1
auto eth1
iface eth1 inet static
    address 192.168.3.100/24
EOF
```
3. set the DNS server:

The file /etc/resolv.conf must contain the following:
```
nameserver 8.8.8.8
nameserver 8.8.4.4
```

4. restart network with: `sudo rc-service networking restart`

Configure `git`, download Github repository in `~/towercomputers/tools` and install `hatch` with:

```
$> ~/install-dev.sh <git-name> <git-email> <git-private-key-path>
```

## 2. Test with hatch

```
$> cd ~/towercomputers/tools
$> hatch run tower --help
$> hatch run build-tower-image --help
```

## 3. Manually QA TowerOS-ThinClient release

On first boot:

1. Basic checking

- Welcome message should be customized.
- README, whitepaper and install-dev.sh should be in ~/.
- wheel package and host image should be in ~/.cache/tower/builds.
- iptables -L -v should show firewall rules and /var/logs/iptables.log should contain firewall logs.
- `lo` and `eth0` should be up (check  with `ip ad`)

2. Provision an online host:

```
$> tower provision web --online --wlan-ssid <ssid> --wlan-password <password> --sd-card /dev/sdb 
```

3. Provision an offline host:

```
$> tower provision office --offline --sd-card /dev/sdb
```

4. Check status:

```
$> tower status
```

5. Install package in offline host:

```
$> tower install office xcalc --online-host office
```

6. Install package in online host:

```
$> tower install web midori
```

7. Test installed packages

```
$> startx
$> tower run office xcalc
$> tower run web midori
```

Check also if the Application menu contains shortcuts for installed packages.

8. Logout from `xfce` and connect to internet as explained above

9. Build an host image with:

```
$> buld-tower-image host
```

10. Build a thinclient image with:

```
$> buld-tower-image thinclient
```

11. Install development environment with:

```
$> ~/install-dev.sh <git-name> <git-email> <git-private-key-path>
```

12. If you are brave redo all these tests with the image generated in step 10 :)

## 4. Build you own custom Thin Client (Linux)

### 4.1. Install dependencies

```
$> apk add alpine-base coreutils python3 py3-pip py3-rich sudo openssh dhcpcd avahi \
      avahi-tools wpa_supplicant rsync git iptables rsync lsblk perl-utils xz \
      musl-locales e2fsprogs-extra nx-libs xsetroot mcookie parted lsscsi figlet \
      alpine-sdk build-base apk-tools acct acct-openrc alpine-conf sfdisk busybox \
      fakeroot syslinux xorriso squashfs-tools mtools dosfstools grub-efi abuild \
      agetty runuser nano vim net-tools losetup xorg-server xf86-input-libinput \
      xinit udev xfce4 xfce4-terminal xfce4-screensaver adw-gtk3 \
      adwaita-xfce-icon-theme setxkbmap
```

### 4.2. Enable services

If necessary, enable IPv4 with:

```
sed -i 's/noipv4ll/#noipv4ll/' /etc/dhcpcd.conf
```

then

```
$> rc-update add dhcpcd
$> rc-update add avahi-daemon
$> rc-update add iptables
$> rc-update add networking
$> rc-update add wpa_supplicant boot
$> rc-update add dbus
```

**Important:** Make sure you are connected to the switch and check that your first wired interface (starting with the letter `e`) has an assigned IP.

### 4.3. Update `/etc/sudoers` and groups

`tower-tools` assumes that the current user has full `sudo` access, with no password. (Please refer to our threat model.) Check if /etc/sudoers contains the following line:

```
<you_username> ALL=(ALL) NOPASSWD: ALL
```

To build an image with `build-tower-image` you need to add the current user in the `abuild` group:

```
addgroup <you_username> abuild
```

### 4.4. Install `tower-tools`

Update pip to the latest version:

```
$> python3 -m pip install --upgrade pip
```

then:

```
$> python3 -m pip install "tower-tools @ git+ssh://github.com/towercomputers/tools.git"
```
