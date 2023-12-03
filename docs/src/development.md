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

## Manually QA TowerOS

### TowerOS-ThinClient Installation

- The USB key containing the `boot` partition must be inserted into the thinclient to boot.
- Secure Boot must be active if the option was selected during installation.
- A welcome message should indicate the location of the documentation.
- The username chosen during installation is correctly created with the chosen password.
- The keyboard and timezone are correctly configured.
- The `swap` partition must be 8Gb, the `home` partition must occupy 20% of the rest, and the `root` partition the remaining space. All these partitions must be encrypted. To check, `lsblk` should display something like this:

        NAME           MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINTS
        sda              8:0    0 232.9G  0 disk  
        └─sda1           8:1    0 232.9G  0 part  
          └─lvmcrypt   253:0    0 232.9G  0 crypt 
            ├─vg0-swap 253:1    0     8G  0 lvm   
            ├─vg0-home 253:2    0    45G  0 lvm   /home
            └─vg0-root 253:3    0 179.9G  0 lvm   /

- `labwc` starts automatically after login if the option was chosen during installation.
- The documentation must be present in the ~/docs folder and can be consulted with the `bat` tool.
- The firewall must be correctly configured and activated (`sudo rc-service iptables status` and `iptables -L -v`).
- `eth0` must be configured with IP `192.168.2.100` and `eth0` with IP `192.168.3.100` (check with `ip ad`).
- On reboot the MAC of `eth0` and `eth1` should not change (check with `ip ad`).
- `labwc` and `sfwbar` should properly start with `dbus-launch labwc`.
- The shell prompt must be in the form of `[<username>@thinclient <current folder>]$`.
- `XDG_RUNTIME_DIR` must be set (check with `echo $XDG_RUNTIME_DIR`).
- `supercronic` service must be started (check with `sudo rc-service supercronic status`).
- Wifi and bluetooth must be soft blocked (check with `rfkill list`).
- Default user should be able to use sudo without password (check with `sudo su`).
- When `labwc` is started, the screen locker should activate correctly after 5 minutes of inactivity.
- `CopyQ` must be correctly started (check the presence of the icon in the taskbar).
- The latest version of `tower` cli must be installed (check with `tower version`).

### Hosts provisioning

- The provisioning of the `router`, an online host and an offline host must work correctly.
- The USB key containing the `boot` partition must be inserted into the host to boot.
- `tower status` should display all hosts with status `up`.
- Hosts must be accessible with `ssh` simply with their name (check with `ssh <host>`).
- The default user, keyboard and timezone should be the same as for the thinclient.
- Online hosts must be connected and offline hosts must not (check with `ssh <host> ping www.google.com`).
- The firewall must be correctly configured and activated (`ssh <host> sudo rc-service iptables status` and `ssh <host> iptables -L -v`).
- `eth0` must be configured on the network `192.168.2.0/24` for online hosts and `192.168.3.0/24` for offline hosts (check with `ip ad`).
- On the `router` the MAC of `wlan0` must be different at each startup.
- The `home` partition must occupy 20% and the `root` partition the remaining space. All these partitions must be encrypted. To check, `ssh <host> lsblk` should display something like this:

        NAME         MAJ:MIN RM  SIZE RO TYPE  MOUNTPOINTS
        sda            8:0    1 28.7G  0 disk  
        └─sda1         8:1    1  512M  0 part  
        mmcblk0      179:0    0 29.7G  0 disk  
        └─lvmcrypt   254:0    0 29.7G  0 crypt 
          ├─vg0-home 254:1    0  5.9G  0 lvm   /home
          └─vg0-root 254:2    0 23.8G  0 lvm   /

- `XDG_RUNTIME_DIR` must be set (check with `ssh <host> echo $XDG_RUNTIME_DIR`).
- The shell prompt must be in the form of `[<username>@<host> <current folder>]$` and be of different color for each host.
- Wifi and bluetooth must be soft blocked except wifi in the `router` (check with `ssh <host> rfkill list`).
- Host default user should be able to use sudo without password (check with `ssh <host> sudo su`).
- The hosts should appear in the `labwc` taskbar with a green icon for the 'up' hosts and a red icon for the 'down' hosts (test by turning off one of the hosts)

### Execution and installation of applications

Once the `router` is installed:

- APK packages must be correctly installed on the hosts with `tower install <host> <package>` and on the thinclient with `tower install thinclient <package>`.
- Once installed, graphical applications should appear in the `sfwbar` menu with icons.
- In the menu the applications are classified by host and each host is differentiated by a colored circle.
- For each host the color of the circle is the same as that of the shell prompt (check with `ssh <host>`).
- `ssh <host>` should not display any welcome message.
- Graphical applications can be launched via the `sfwbar` menu or terminal with `tower <host> run <application>`.
- Copy/paste must be possible between two graphics applications running on different hosts.
- Online applications must work correctly on online hosts (check for example that it is possible to browse the web with Midori).
- The `tor` proxy must be accessible from online hosts (check with `ssh web curl --socks5 192.168.2.1:9050 https://check.torproject.org/api/ip`).
- The time on online hosts must be correct (thanks to `chronyd`).

### TowerOS-ThinClient Upgrade

In addition to all the points listed for installing TowerOS-ThinClient:

- The new version of `tower` cli must be installed (check with `tower version`).
- All previously installed hosts must be accessible (check with `tower status`).
- The `sfwbar` menu must display all applications previously installed on the hosts.
- The `sfwbar` widget indicating the host status must be active.
- The contents of the home partition must be completely preserved.

### Host Upgrade

In addition to all the points listed for Hosts provisioning:

- The new version of TowerOS-Host must be installed (check with `tower status`).
- All applications installed with `tower install` must be reinstalled.
- The contents of the host home partition must be completely preserved.
