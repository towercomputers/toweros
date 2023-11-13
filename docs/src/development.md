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

## Build TowerOS images

Connect to internet and download Github repository as explained in the first paragraph above.

### TowerOS Host

```
[thinclient]$ cd ~/towercomputers/toweros/tower-build-cli
[thinclient]$ ./tower-build host
```

This will generate a TowerOS-Host image file compressed with xz in `~/.cache/tower/builds/`. Images in this folder will be used by default by the `provision` command (if the `--image` flag is not provided).

### TowerOS Thin Client

```
[thinclient]$ ./tower-build thinclient
```

This will generate an ISO image in `~/.cache/tower/builds/`. A TowerOS Host image is embedded in the TowerOS ThinClient image. If a TowerOS Host image is present in the `~/.cache/tower/builds/` folder, it is used. Otherwise a new image is automatically generated.

### With Docker

Build the Docker image with:

```
[thinclient]$ git clone git@github.com:towercomputers/toweros.git
[thinclient]$ cd toweros/tower-build-cli
[thinclient]$ docker build -t build-tower-image:latest -f ./Dockerfile ../
```

Then build the TowerOS image inside a Docker container:

```
[thinclient]$ docker run --name towerbuilder --user tower --privileged -v /dev:/dev build-tower-image thinclient
```

Retrieve that image from the container:

```
[thinclient]$ docker cp towerbuilder:/home/tower/.cache/tower/builds/toweros-thinclient-0.0.1-20230513171731-x86_64.iso ./
```

Finally delete the container with:

```
[thinclient]$ docker rm towerbuilder
```

**Note: **With the ARM64 architecture, you must use `buildx` and a cross-platform emulator like `tonistiigi/binfmt`.

```
[thinclient]$ docker buildx create --use
[thinclient]$ docker buildx build -t build-tower-image:latest --platform=linux/amd64 --output type=docker -f ./Dockerfile ../
[thinclient]$ docker run --privileged --rm tonistiigi/binfmt --install all
[thinclient]$ docker run --platform=linux/amd64 --name towerbuilder --user tower --privileged -v /dev:/dev \
              build-tower-image thinclient
```

## Manually QA TowerOS for Thin Client

On first boot:

1. Basic checking

    - The “welcome message” should refer to TowerOS.
    - The README, whitepaper and `install-dev.sh` script should be found in `~/`.
    - The `wheel` package and host image should be in `~/.cache/tower/builds`.
    - `$ iptables -L -v` should show firewall rules, and `/var/logs/iptables.log` should contain firewall logs.
    - `lo` and `eth0` should be up (check  with `$ ip ad`)

1. Provision an online host:

        [thinclient]$ tower provision router --wlan-ssid <ssid> --wlan-password <password>
        [thinclient]$ tower provision web --online

1. Provision an offline host:

        [thinclient]$ tower provision office --offline

1. Check system status:

        [thinclient]$ tower status

1. Install a package in an offline host:

        [thinclient]$ tower install office xcalc

1. Install a package in an online host:

        [thinclient]$ tower install web midori

1. Test installed packages:

        [thinclient]$ startx
        [thinclient]$ tower run office xcalc
        [thinclient]$ tower run web midori

    Check also if the Xfce Application menu contains shortcuts for installed packages.

## Build your own custom Thin Client (Linux)

### Install Dependencies

```
[thinclient]$ apk add alpine-base coreutils python3 py3-pip py3-rich sudo openssh dhcpcd avahi \
      avahi-tools wpa_supplicant rsync git iptables rsync lsblk perl-utils xz \
      musl-locales e2fsprogs-extra nx-libs xsetroot mcookie parted lsscsi figlet \
      alpine-sdk build-base apk-tools acct acct-openrc alpine-conf sfdisk busybox \
      fakeroot syslinux xorriso squashfs-tools mtools dosfstools grub-efi abuild \
      agetty runuser nano vim net-tools losetup xorg-server xf86-input-libinput \
      xinit udev xfce4 xfce4-terminal xfce4-screensaver adw-gtk3 \
      adwaita-xfce-icon-theme setxkbmap
```

### Enable Basic Services

If necessary, enable IPv4 with:

```
[thinclient]$ sed -i 's/noipv4ll/#noipv4ll/' /etc/dhcpcd.conf
```

then

```
[thinclient]$ rc-update add dhcpcd
[thinclient]$ rc-update add avahi-daemon
[thinclient]$ rc-update add iptables
[thinclient]$ rc-update add networking
[thinclient]$ rc-update add wpa_supplicant boot
[thinclient]$ rc-update add dbus
```

**Important:** Make sure you are connected to the switch and check that your first wired interface (starting with the letter `e`) has an assigned IP.

### Update `/etc/sudoers` and groups

The `toweros` software assumes that the current user has full `sudo` access with no password. (Please refer to our [threat model](security.md).) Check if `/etc/sudoers` contains the following line:

```
<your_username> ALL=(ALL) NOPASSWD: ALL
```

To build an image with `./tower-build`, you first need to add the current user in the `abuild` group:

```
[thinclient]$ addgroup <you_username> abuild
```

### Install `tower-cli`

Update `pip` to the latest version:

```
[thinclient]$ python3 -m pip install --upgrade pip
```

Install the `tower` CLI with `pip`:

```
[thinclient]$ python3 -m pip install "tower-cli @ git+https://github.com/towercomputers/toweros.git#subdirectory=tower-cli"
```

