## 1. Installation

### 1.1. Hardware configuration

You must have a Thin Client (typically a laptop like a Lenovo X270) connected to a switch and one or more Raspberry PI 4 computers connected on the same switch.

### 1.2. TowerOS-ThinClient

The easiest way to use Tower is to run the TowerOS-ThinClient GNU/Linux distribution (based on Alpine Linux) on your Thin Client.

To install get TowerOS-ThinClient:

1. Download the latest image here: [https://drive.google.com/file/d/1xpC7BlrOa0LaHNuQ4-SQUiOGassmMb-x/view?usp=sharing](https://drive.google.com/file/d/1xpC7BlrOa0LaHNuQ4-SQUiOGassmMb-x/view?usp=sharing).
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
