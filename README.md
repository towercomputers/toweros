# Tower

**Tower** is a computer system for paranoid individuals and high-value targets that turns the existing paradigm for computer security on its head: Instead of taking a single computer and splitting it into multiple security domains at the level of the operating system or hypervisor (cf. [AppArmor](https://apparmor.net/) and [QubesOS](https://www.qubes-os.org/)), Tower combines *multiple, independent computers* into a single, unified, virtual system with a shared, composited user interface. Each security domain is regelated to a separate, dedicated *Host* (e.g. a Raspberry Pi), and the user accesses their applications from a *Thin Client* (e.g. a laptop) over a LAN using standard network protocols (namely, SSH and NX), following strict firewall rules that govern all network communication.

Technically speaking, Tower is an example of a *converged multi-level secure (MLS) computing system*. In contrast to existing designs, Tower offers theoretically greater security guarantees, better usability, and more flexibility. The downside, of course, is that you need multiple computers to make it work. But with the development of cheap, powerful and small single-board computers (SBCs), it's now quite practical to carry half a dozen computers with you wherever you go. So, instead of having to trust your operating system or hypervisor to be able properly to isolate different security domains all running on shared hardware, you can rely on standard, open-source implementations of widely used networking protocols, to connect multiple independent computers together to form a single, virtual device that functions very much like a normal desktop or laptop.

This repository represents an OSS implementation of the above design. It includes within it tools for the following purposes:

1. Provisioning and maintaining the Thin Client
2. Provisioning, maintaining and monitoring the various Hosts
3. Managing the network layer (provisioning the Switch, enforcing firewall rules, etc.)

For a more formal description of the Tower architecture, including a comparison with Qubes OS, please refer to [the whitepaper](docs/Tower%20Whitepaper.pdf).


* 1.[ Installation](#1-installation)
  * 1.1. [Hardware configuration](#11-hardware-configuration)
  * 1.2. [TowerOS-ThinClient](#12-toweros-thin-client)
    * 1.2.1. [Notes about TowerOS-ThinClient](#122-notes-about-toweros-thinclient)
  * 1.3. [Custom Thin Client (Linux)](#13-custom-thin-client-linux)
    * 1.3.1. [Install dependencies](#131-install-dependencies)
    * 1.3.2. [Enable services](#132-enable-services)
    * 1.3.3. [Prepare networks](#133-prepare-networks)
    * 1.3.4. [Update /etc/sudoers](#134-update-etcsudoers)
    * 1.3.5. [Install `tower-tools`](#135-install-tower-tools)
* 2.[ Usage](#2-usage)
  * 2.1. [Provision a Host](#21-provision-a-host)
    * 2.1.1. [Generate an image with build-image](#211-generate-an-image-with-build-image)
    * 2.1.2. [Prepare the SD card](#212-prepare-the-sd-card)
  * 2.2. [Execute a command in one of the hosts](#22-execute-a-command-in-one-of-the-hosts)
  * 2.3. [Install an application on one of the hosts](#23-install-an-application-on-one-of-the-hosts)
  * 2.4. [List hosts and their status](#24-list-hosts-and-their-status)
  * 2.5. [Example using two hosts](#25-example-using-two-hosts)
  * 2.6. [Build a TowerOS image with Docker](#27-build-a-toweros-image-with-docker)
* 3.[ Implementation](#3-implementation)
  * 3.1. [Network architecture](#31-network-architecture)
  * 3.2. [TowerOS-ThinClient](#32-toweros-thinclient)
  * 3.3. [TowerOS-Host](#33-toweros-host)
  * 3.4. [SSHConf](#34-sshconf)
  * 3.5. [Provision](#35-provision)
  * 3.6. [GUI](#36-gui)
  * 3.7. [Install](#37-install)

## 1. Installation

### 1.1. Hardware configuration

You must have a Thin Client (typically a laptop like a Lenovo X270) connected to TWO unmanaged switches and one or more Raspberry PI 4 computers connected on the same switches.

### 1.2. TowerOS-ThinClient

The easiest way to use Tower is to run the TowerOS-ThinClient GNU/Linux distribution (based on Alpine Linux) on your Thin Client.

To install get TowerOS-ThinClient:

1. Download the latest image here: [https://github.com/towercomputers/tools/releases/download/v0.1.0/toweros-thinclient-0.1.0-x86_64.iso](https://github.com/towercomputers/tools/releases/download/v0.1.0/toweros-thinclient-0.1.0-x86_64.iso).
2. Prepare a bootable USB medium using the above image.
3. Boot the Thin Client with the USB drive and follow the instructions.

Note: you can build your own image of TowerOS with command `build-tower-image thinclient` or with Docker (see below).

#### 1.2.1. Notes about TowerOS-ThinClient

* The TowerOS-ThinClient install scripts generally follow the official Alpine Linux install guide (see [https://wiki.alpinelinux.org/wiki/Installation](https://wiki.alpinelinux.org/wiki/Installation)) 
* The installer sets up an `iptables` firewall as described here [https://wiki.archlinux.org/title/Simple_stateful_firewall](https://wiki.archlinux.org/title/Simple_stateful_firewall).
* `syslog-ng` is configured to log `iptables` events in /var/log/iptables.log 
* TowerOS-ThinClient uses `Syslinux` as the boot loader.

### 1.3. Custom Thin Client (Linux)

If you have installed toweros-thinclient you don't need to perform this step, you can skip to paragraph 2 (Usage).

#### 1.3.1. Install dependencies

```
$> apk add alpine-base coreutils python3 py3-pip py3-rich sudo openssh rsync git \
          iptables lsblk perl-utils xz musl-locales e2fsprogs-extra nx-libs xsetroot \
          mcookie parted lsscsi figlet alpine-sdk build-base apk-tools acct acct-openrc \
          alpine-conf sfdisk busybox fakeroot syslinux xorriso squashfs-tools mtools \
          dosfstools grub-efi abuild agetty runuser nano vim net-tools losetup \
          xorg-server xf86-input-libinput xinit udev xfce4 xfce4-terminal xfce4-screensaver \
          xfce4-clipman-plugin adw-gtk3 adwaita-xfce-icon-theme setxkbmap syslog-ng
```

#### 1.3.2. Enable services

If necessary, enable IPv4 with:

```
sed -i 's/noipv4ll/#noipv4ll/' /etc/dhcpcd.conf
```

then

```
$> rc-update add iptables
$> rc-update add networking
$> rc-update add dbus
```

#### 1.3.3. Prepare networks

Make sure you are connected to the two switches and check that your wired interfaces (starting with the letter `e`).

The file /etc/network/interfaces must contain the following:

```
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
    address 192.168.2.100/24
iface eth1 inet static
    address 192.168.3.100/24
EOF
```

#### 1.3.4. Update `/etc/sudoers` and groups

`tower-tools` assumes that the current user has full `sudo` access, with no password. (Please refer to our threat model.) Check if /etc/sudoers contains the following line:

```
<you_username> ALL=(ALL) NOPASSWD: ALL
```

To build an image with `build-tower-image` you need to add the current user in the `abuild` group:

```
addgroup <you_username> abuild
```

#### 1.3.5. Install `tower-tools`

Update pip to the latest version:

```
$> python3 -m pip install --upgrade pip
```

then:

```
$> python3 -m pip install "tower-tools @ git+ssh://github.com/towercomputers/tools.git"
```

## 2. Usage

### 2.1. Provision a host

Note: If you are using TowerOS, you can skip the first step.

#### 2.1.1. Generate an image with build-image

```
$> build-tower-image host
```

This will generate an image file compressed with xz in `~/.cache/tower/builds/`. Images in this folder will be used by default by the provision command if the `--image` flag is not provided.

#### 2.1.2. Prepare the SD card

For offline host:

```
$> tower provision <host> --offline
```

The sd-card must be inserted in a RPI connected to the offline network (`eth1` of the thinclient)

To provision an online host you must first provision the `router`:

```
$> tower provision router --wlan-ssid <ssid> --wlan-password <password>
```

and then:

```
$> tower provision <host> --online
```

The sd-cards of the `router` and online hosts must be inserted in a RPI connected to the online network (`eth0` of the thinclient)

Keyboard, timezone and lang are retrieved from the Thin Client. You can customize them with the appropriate argument (see `tower provision --help`).

To update the wifi settings of the router you can use the command `wlan-connect`:

```
$> tower provision wlan-connect --ssid <ssid> --password <password>
```

### 2.2. Execute a command on one of the hosts

Run a command on a host with SSH:

```
$> ssh <host> ls ~/
```

or a graphical application with NX protocol:

```
$> tower run <host> <application-name>
```

### 2.3. Install an application on one of the hosts

```
$> tower install <host> <application-name>
```

or, if the host is offline, you can tunnel the installation through an online host:

```
$> tower install <offline-host> <application-name> --online-host <online-host> 
```

### 2.4. List hosts and their statuses

```
$> tower status
```

### 2.5. Example using two hosts

Provision the first offline host named `office`.

```
$> tower provision office
```

Provision a second online host named `web`.

```
$> tower provision web --online –wlan-ssid <ssid> –wlan-password <password>
```

Install galculator on the `office` offline host.

```
$> tower install office galculator --online-host=web
```

Run galculator from `office`.

```
$> startx
$> tower run office gcalculator
```

### 2.6. Build a TowerOS image with Docker

Build the Docker image with:

```
$> git clone git@github.com:towercomputers/tools.git
$> cd tools
$> hatch build -t wheel
$> docker build -t build-tower-image:latest .
```

Then build the TowerOS image inside a Docker container:

```
$> docker run --name towerbuilder --user tower --privileged -v /dev:/dev build-tower-image thinclient
```

Retrieve that image from the container:

```
$> docker cp towerbuilder:/home/tower/.cache/tower/builds/toweros-thinclient-0.0.1-20230513171731-x86_64.iso ./
```

Finally delete the container with:

```
$> docker rm towerbuilder
```

**Note: **With the ARM64 architecture, you must use `buildx` and a cross-platform emulator like `tonistiigi/binfmt`.

```
$> docker buildx create --use
$> docker buildx build -t build-tower-image:latest --platform=linux/amd64 --output type=docker .
$> docker run --privileged --rm tonistiigi/binfmt --install all
$> docker run --platform=linux/amd64 --name towerbuilder --user tower --privileged -v /dev:/dev \
              build-tower-image thinclient
```

## 3. Implementation

To date, `tower-tools` includes six main modules: `buildthinclient.py` and `buildhost.py` to build the OS images used by the `thinclient` and the hosts. `sshconf.py` which manages `tower-tools` and `ssh` configuration files. `provision.py`, `install.py`, and `gui.py` which respectively allow you to provision a host, to install an application on it even without an internet connection and to run a graphical application of a host from the `thinclient`.

### 3.1. Network architecture

The thinclient is connected to two separate networks (via two distinct switches), one connected to the internet, the other offline. The hosts supposed to have a connection are connected to the first network, and those which should be offline are connected to the second.
On the online network, one of the hosts, called the `router`, is connected to the internet and shares the connection with all the hosts connected to the same network.
All IPs are static and assigned by the `tower` tool. Here are the IPs used:

TOWER_NETWORK_ONLINE = "192.168.2.0/24"
TOWER_NETWORK_OFFLINE = "192.168.3.0/24"
THIN_CLIENT_IP_ETH0 = "192.168.2.100"
THIN_CLIENT_IP_ETH1 = "192.168.3.100"
ROUTER_IP = "192.168.2.1"
FIRST_HOST_IP = 200 # 192.168.2.200 or 192.168.3.200

### 3.2. TowerOS-ThinClient

`buildthinclient.py` is the module responsible for generating an image of TowerOS with the `build-tower-image thinclient` command.

TowerOS is based on Alpine Linux, and `buildthinclient.py` uses the `mkimage` tool (see https://wiki.alpinelinux.org/wiki/How_to_make_a_custom_ISO_image_with_mkimage).

The installer contains all the apk and pip packages necessary for installing the base system and `tower-tools`, which is ready to use from the first boot. In this way, the installation of the system, as well as the provisioning of a first host, does not require an Internet connection.

Here are the different steps taken by `buildthinclient.py` to generate an image:

1. Gathering the necessary builds.
The script starts by checking for the existence of a `./dist`, `./builds` or `~/.cache/tower/builds/` folder. If one of them exists, this is where the script will fetch the builds and place the final image. If no folder exists, then the script creates the folder `~/.cache/tower/builds/`. Next:

    1. The script then verifies that the TowerOS-Host image is present. If not, it launches the build of a new image (cf. TowerOS-Host). 
    2. The script checks for the existence of a `tower-tools` wheel package. If it does not exist the package is retrieved from Github.

2. Downloading pip packages with `pip download` in a cache folder

4. Creating and updating an Alpine APK overlay folder with mainly:

    1. `pip` cache folder
    2. add  system install bash scripts (see https://github.com/towercomputers/tools/tree/dev/scripts/toweros-thinclient)
    3. add the Towercomputers documentation
    4. Add /etc configuration files
    5. add builds required by `tower-tools` (TowerOS-Host, `tower-tools`)

5. Launch of `mkimage` which takes care of the rest.

6. Renaming and copying the image into the `builds` folder.

7. Cleaning temporary files.


### 3.3. TowerOS-Host

`buildhost.py` is the module responsible for generating an image of TowerOS-ThinClient when the `build-tower-image host` command is executed and also for configuring the image when the `tower provision` command is called.

`buildhost.py` uses the same method as `pigen` to build an image for a Raspberry PI (see [https://github.com/RPi-Distro/pi-gen/blob/master/export-image/prerun.sh](https://github.com/RPi-Distro/pi-gen/blob/master/export-image/prerun.sh)) but unlike `pigen` which uses a Debian-based system, `buildhost.py` uses an Alpine Linux-based system (see https://wiki.alpinelinux.org/wiki/Classic_install_or_sys_mode_on_Raspberry_Pi).

TowerOS-ThinClient must be used with the `tower provision` command which finalises the configuration of the image which is otherwise neither secure (no firewall in particular) nor ready to be used by `tower-tools`.

Here are the different steps taken by `buildhost.py` to generate an image:

1. Installing an Alpine Linux system in a mounted temporary folder:

    1. creating an image file with `mkfs.ext4`
    2. mount this image with `mount`
    3. installation of a minimalist Alpine Linux system and NX in the mounted folder ([https://dl-cdn.alpinelinux.org/alpine/v3.17/releases/armv7/alpine-rpi-3.17.3-armv7.tar.gz](https://dl-cdn.alpinelinux.org/alpine/v3.17/releases/armv7/alpine-rpi-3.17.3-armv7.tar.gz))

2. creation with `parted`, in an image file, of the partitions necessary for a Raspberry PI with the size adapted for the system installed in step 1.

3. copy, with `rsync`, the system installed in step 1 into the partitions created in step 2.

4. compression of the image containing the partitions from step 2.

5. Unmounting and cleaning files and temporary folders.

Here are the different steps taken by `buildhost.py` to configure an image when provisioning an host:

1. copy image to sd-card

2. expand root partition to occupy entire sd-card

3. places a `tower.env` file in the root of the boot partition. This file contains all the variables needed to install the system on first boot (HOSTNAME, USERNAME, PUBLIC_KEY, ...).

4. unmount the sd-card which is ready to be inserted into the RPI

Note: A TowerOS-ThinClient image is placed in the `~/.cache/tower/builds/` folder by the TowerOS installer.

### 3.4. SSHConf

`tower-tools` uses a single configuration file in the same format as an SSH config file: `~/.ssh/tower.conf`. This file, included in `~/.ssh/config`, is used both by `tower-tools` to maintain the list of hosts and by `ssh` to access hosts directly with `ssh <host>`. `sshconf.py` is responsible for maintaining this file and generally anything that requires manipulation of something in the `~./ssh` folder. Notably:

1. to discover the IP of a newly installed host and update `tower.conf`
2. update `~/.ssh/know_hosts`
3. check the status of a host and if he is online.

Note: `sshconf.py` uses [https://pypi.org/project/sshconf/](https://pypi.org/project/sshconf/) to manipulate `ssh` config files.

### 3.5. Provision

`provision.py` is used by the `tower provision <host>` command to prepare an SD card directly usable by a Rasbperry PI.

The steps to provision a host are as follows:

1. generation of a key pair.
2. generation of the host configuration (`tower.env` file), with the values provided on the command line, or with those retrieved from the `thinclient`.
3. copy of the TowerOS-ThinClient image on the SD card and insertion of the configuration file.
4. waiting for the new host to be detected on the network after the user inserts the sd-card in the RPI and the boot is finished.
5. updated `ssh` and `tower-tools` configuration file.

Once a host is provisioned it is therefore directly accessible by ssh with `ssh <host>` or `tower run <host>`.

### 3.6. GUI

GUI is a module that allows the use of the NX protocol through an SSH tunnel. It allows to execute from the `thinclient` a graphical application installed on one of the hosts with `tower run <host> <application-name>application>`.

`nxagent` must be installed in the host and `nxproxy` in the `thinclient`. Of course both are pre-installed in TowerOS and TowerOS-ThinClient.

Here are the steps taken by `gui.py` to run an application on one of the hosts:

1. Generation of a unique cookie which is added in the host with `xauth add`.

2. With `ssh` launch `nxagent` on the host which only accepts local connections.

3. With the same command line, open a tunnel between the host and the `thinclient` on the port of `nxagent`.

4. Launch `nxproxy` with the cookie generated in step 1 and on the same port as the tunnel opened in step 3.

5. At this stage `nxproxy` and `nxagent` are connected and we have a "virtual screen" on which we run the graphical application with: `ssh <host> DISPLAY=:50 <application-name>application>`.

6. When the application launched in the previous step is closed, `gui.py`

    1. closes `nxagent` and the tunnel opened in step 2 and 3.
    2. revokes the cookie from step 1 with `xauth remove`
    3. closes `nxproxy`

GUI works the same way as X2GO from which it is directly inspired.

### 3.7. Install

This module allows to use `apk` on an offline host through an `ssh` tunnel to an online host. To do this it performs the following steps:

1. Preparing the offline host to redirect requests to the `apk` repository to the `thinclient`:
    1. Added a `127.0.0.1 <apk_repo_host>` entry in the `/etc/hosts` file
    2. Added an `iptables` rule to redirect requests on port 80 to port 4443 (so you don't need to open the tunnel in `root` because port 80 is protected).
    3. Preparation of a pacman.conf file containing only the `apk_repo_host`.
    4. Opening a tunnel to redirect port 4443 of the offline host to port 4666 of the `thinclient`.

2. Open a tunnel to redirect port 4666 from `thinclient` to the apk repository host on the online host with: `ssh -R 4666:<apk_repo_host>:80 <online-host>`.

3. At this point the module can normally use `apk` with `ssh` on the offline host to install the desired packages.

4. Once the installation is finished, clean the `/etc/hosts` file and the `iptables` rules on the offline host and close the ssh tunnels.

Note: when installing each package, `apk` verifies that it has been signed by the authors and maintainers of Alpine Linux. Therefore it is not necessary to trust the online host but above all to initialise the apk keys in a trusted environment. This means for us that it is imperative to build the images of TowerOS and TowerOS-ThinClient in a trusted environment and to manually verify the keys.
