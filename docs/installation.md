## 1. Installation

### 1.1. Hardware configuration

![Tower Archi](../img/towerarchi.png)

To use Tower you need a Thin Client and several Hosts connected via one or ideally two switches.

The Thin Client is typically a laptop like the Lenovo X270. An SD-card reader is necessary for the Thin Client to prepare the SD-cards containing the hosts' OS. Two RJ45 ports are also necessary to connect the Thin Client to the two switches (you can optionally use a USB ethernet adapter).

For the moment tower has been tested with two types of hosts: Raspberry PI 4b and Compute Module 4 Lite.

1.1.1. Raspberry PI 4b

For each Raspberry PI you need:

- an SD card, for the boot partition
- a USB key which will serve as a hard drive.
- for offline hosts a Real Time Clock hat

Tips:

- Remember to plug the USB key into the blue port (USB 3.0)
- For hosts that serve as a router we recommend an RPI with 2GB of RAM, for others, especially if you plan to run graphicals applications, we recommend 8GB of RAM.
- for sd-cards and usb keys, look at the list of hardware that we tested and their performance (TODO)

1.1.1. Compute Module 4 Lite

![Deskpi Super6c board](../img/deskpi.jpg)

Using CM4s and the [Deskpi Super6c board](https://deskpi.com/collections/deskpi-super6c/products/deskpi-super6c-raspberry-pi-cm4-cluster-mini-itx-board-6-rpi-cm4-supported) you can avoid most cables and put all your hosts in an ATX case.

For each CM4 you need:

- an SD card, for the boot partition
- a NVMe M.2 SS2 which will serve as a hard drive.

One of the CM4s, the one that will serve as a router, must have WiFi and 2GB of RAM is sufficient. For other hosts, WiFi is not necessary, but we recommend 8GB of RAM, especially for hosts that need to run graphicals applications.

Ideally you should use two Deskpis, one for online hosts and another for offline hosts.

### 1.2. TowerOS-ThinClient

The easiest way to use Tower is to run the TowerOS-ThinClient GNU/Linux distribution (based on Alpine Linux) on your Thin Client.

To install get TowerOS-ThinClient:

1. Download the latest image here: [https://github.com/towercomputers/tools/releases/latest](https://github.com/towercomputers/tools/releases/latest).
2. Prepare a bootable USB medium using the above image.
3. Boot the Thin Client with the USB drive and follow the instructions.

Note: you can build your own image of TowerOS with command `build-tower-image thinclient` or with Docker (see below).

### 1.3. Custom Thin Client (Linux)

#### 1.3.1. Install dependencies

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

#### 1.3.2. Enable services

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

#### 1.3.3. Update `/etc/sudoers` and groups

`tower-tools` assumes that the current user has full `sudo` access, with no password. (Please refer to our threat model.) Check if /etc/sudoers contains the following line:

```
<you_username> ALL=(ALL) NOPASSWD: ALL
```

To build an image with `build-tower-image` you need to add the current user in the `abuild` group:

```
addgroup <you_username> abuild
```

#### 1.3.4. Install `tower-tools`

Update pip to the latest version:

```
$> python3 -m pip install --upgrade pip
```

then:

```
$> python3 -m pip install "tower-tools @ git+ssh://github.com/towercomputers/tools.git"
```
