# Implementation

TowerOS is built on [Alpine Linux](https://alpinelinux.org), because of Alpine's simplicity, minimalism, and security-first approach. TowerOS is open-source and freely licensed (under the Apache License 2.0). It is designed to require the smallest-possible trusted computing base, to rely only on other widely used open-source software, and to be as transparent as possible in its implementation.


## Tower Tools

The `toweros` package contains all of the tooling necessary to build TowerOS images for both the thin client and for the hosts (a pre-built image for the thin client—containing a pre-built image for hosts---is available on the [GitHub Releases](https://github.com/towercomputers/toweros/releases) page).

This package is organized into six primary modules:

- `buildthinclient.py` and `buildhost.py` to build the OS images used by the thin client and the hosts
- `sshconf.py` which manages TowerOS and SSH configuration files
- `provision.py`, `install.py`, and `gui.py` which allow you to provision a host, to install an application on it without an Internet connection, and to run a graphical application on a host from the thin client, respectively.


## Networking

A TowerOS **thin client** connects to one or two separate networks of **hosts** (each network with an unmanaged switch). One network is connected to the Internet; the other (optional) network is offline. *Online* hosts reside on the first network; *offline* hosts on the second. On the online network, one of the hosts is the **router**: it is connected to the Internet directly and shares its connection with all the hosts connected to the same network.

All IPs are static and assigned by the `tower` tool. Here are the IPs used:

* TOWER_NETWORK_ONLINE = "192.168.2.0/24"
* TOWER_NETWORK_OFFLINE = "192.168.3.0/24"
* THIN_CLIENT_IP_ETH0 = "192.168.2.100"
* THIN_CLIENT_IP_ETH1 = "192.168.3.100"
* ROUTER_IP = "192.168.2.1"
* FIRST_HOST_IP = 200 # 192.168.2.200 or 192.168.3.200

### Firewall Rules

Firewalls are a primary element in the security of a TowerOS system. `iptables` is installed and configured on each host and on the thin client using the following two scripts:

* https://github.com/towercomputers/toweros/blob/dev/scripts/toweros-host/installer/configure-firewall.sh
* https://github.com/towercomputers/toweros/blob/dev/scripts/toweros-thinclient/installer/configure-firewall.sh

Both of these scripts are destructive and idempotent: they clean all the rules at the beginning and save the new rules at the end.

The thin client is configured with the [following guide](https://wiki.archlinux.org/title/Simple_stateful_firewall)

Hosts are configured the same way, but with the following additional rules:

- Port 22 is open to the thin client.
- Offline hosts reject all outgoing traffic.
- Online hosts reject outgoing traffic directed to the thin client or to other hosts.
- The router has IP forwarding active, to share its connection with the other online hosts.


## Building your own TowerOS Images

### Image for Thin Clients

`buildthinclient.py` is the module responsible for generating an image of TowerOS with the `build-tower-image thinclient` command, which uses the `mkimage` tool (see <https://wiki.alpinelinux.org/wiki/How_to_make_a_custom_ISO_image_with_mkimage>).

The installer contains all the APK and pip packages necessary for installing the base system and `toweros`, which is ready to use after the first boot. In this way, the installation of the system, as well as the provisioning of a first host, does not require an Internet connection.

Here are the different steps taken by `buildthinclient.py` to generate an image:

1. Gathering the necessary builds.
The script starts by checking for the existence of a `./dist`, `./builds` or `~/.cache/tower/builds/` folder. If one of them exists, this is where the script will fetch the builds and place the final image. If no folder exists, then the script creates the folder `~/.cache/tower/builds/`. Next:

    1. The script then verifies that the TowerOS host image is present. If not, it launches the build of a new image.
    2. The script checks for the existence of a `toweros` wheel package. If it does not exist the package is retrieved from GitHub.

2. Downloading `pip packages with `pip download` in a cache folder

4. Creating and updating an Alpine APK overlay folder, including most importantly:

    1. pip cache folder
    2. Add the system install BASH scripts (see https://github.com/towercomputers/toweros/tree/dev/scripts/toweros-thinclient)
    3. Include the TowerOS documentation
    4. Add the `/etc` configuration files
    5. Add builds required by `toweros` (TowerOS for the host, `toweros`)

5. Launching `mkimage`, which takes care of the rest.

6. Renaming and copying the image into the `builds` folder.

7. Cleaning temporary files.

**Notes about the TowerOS installer for the thin client:**

* The install scripts generally follow the official [Alpine Linux install guide](https://wiki.alpinelinux.org/wiki/Installation).
* The installer sets up an `iptables` firewall as described in the [Arch Linux Wiki](https://wiki.archlinux.org/title/Simple_stateful_firewall).
* The script uses SysLinux as the boot loader.


### Image for Hosts

`buildhost.py` is the module responsible for generating an image for the thin client when the `build-tower-image host` command is executed, and also for configuring the image when the `tower provision` command is called.

`buildhost.py` uses the same method as `pigen` to build an image for a Raspberry Pi (see [https://github.com/RPi-Distro/pi-gen/blob/master/export-image/prerun.sh](https://github.com/RPi-Distro/pi-gen/blob/master/export-image/prerun.sh)) but unlike `pigen`, which uses a Debian-based system, `buildhost.py` uses an Alpine Linux–based system (see https://wiki.alpinelinux.org/wiki/Classic_install_or_sys_mode_on_Raspberry_Pi).

The `tower provision` command finalises the configuration of the image, which is otherwise neither secure nor ready to be used by `toweros`.

Here are the different steps taken by `buildhost.py` to generate an image:

1. Install an Alpine Linux system in a mounted temporary folder:

    1. Create an image file with `mkfs.ext4`
    2. Mount this image with `mount`
    3. Install a minimal Alpine Linux system, as well as NX, in the mounted folder ([https://dl-cdn.alpinelinux.org/alpine/v3.17/releases/armv7/alpine-rpi-3.17.3-armv7.tar.gz](https://dl-cdn.alpinelinux.org/alpine/v3.17/releases/armv7/alpine-rpi-3.17.3-armv7.tar.gz))

2. Create the necessary partitions with `parted` and stores them in an image file, with the sizes adapted for the system installed in step 1.

3. Copy the installed system into the newly-created partitions with `rsync`

4. Compress the image containing the partitions

5. Unmount and cleans up temporary files and folders

Here are the different steps taken by `buildhost.py` to configure an image when provisioning an host:

1. Copy the image to the SD card

2. Grow the root partition to occupy entire SD card

3. Place a `tower.env` file in the root directory of the boot partition. This file contains all the variables needed to install the system on the first boot (`HOSTNAME`, `USERNAME`, `PUBLIC_KEY`, ...).

4. Unmount the SD card, which is ready to be inserted into the host device.

Note: A TowerOS image for the thin client is placed in the `~/.cache/tower/builds/` folder by the installer.


## System Configuration

A TowerOS system uses a single configuration file in the same format as an SSH config file: `~/.ssh/tower.conf`. This file, referenced in `~/.ssh/config`, is used both by `toweros` to maintain the list of hosts and by `ssh` to access hosts directly with `[thinclient]$ ssh <host>`. The script `sshconf.py` is responsible for maintaining this file and generally anything that requires manipulation of something in the `~./ssh` folder. Notably:

1. discovering the IP of a newly installed host and updating `tower.conf` accordingly
2. updating `~/.ssh/know_hosts`
3. checking the status of a host and if it is online

Note: `sshconf.py` uses [https://pypi.org/project/sshconf/](https://pypi.org/project/sshconf/) to manipulate `ssh` config files.


## Host Provisioning

`provision.py` is used by the `tower provision <host>` command to prepare an SD card directly usable by a Rasbperry Pi.

The steps to provision a host are as follows:

1. Gereate a key pair.
2. Generate the host configuration (`tower.env`) with the values provided on the command line or with those retrieved from the thin client
3. Copy of the TowerOS thin client image onto the SD card and include the configuration file
4. Wait for the new host to be detected on the network after the user has inserted the SD card into the host device
5. Update the `ssh` and `toweros` configuration files

Once a host has been provisioned, it should be accessible with `$ ssh <host>` or `$ tower run <host> <command>`.


## GUI Application Execution

`gui.py` is a module that allows the use of the NX protocol through an SSH tunnel: it allows the user run an application on one of the hosts from the safety of the thin client.

`nxagent` must be installed on the host, and `nxproxy` on the thin client. Of course, both are included in the TowerOS images.

Here are the steps taken by `gui.py` to run an application on one of the hosts:

1. Generate a unique cookie which is added in the host with `xauth add`

2. Launch `nxagent` (configured to accept only local connections) on the host using `ssh`

3. Open an SSH tunnel between the host and the thin client on the port used by `nxagent`

4. Launch `nxproxy` with the generated cookie and on the port associated with the SSH tunnel

_At this stage `nxproxy` and `nxagent` are connected, and we have a virtual screen, on which we run the graphical application with: `ssh <host> DISPLAY=:50 <application-name>application>`._


After the application has been closed, `gui.py` will perform the following actions:

1. Terminate `nxagent` and close the SSH tunnel
2. Revoke the cookie with `xauth remove`
3. Terminate `nxproxy`

The GUI system therefor works the same way as X2GO, which provided the inspiration.


## Package Management

This module allows to use of `apk` on an offline host through an SSH tunnel through the router. To do this, it performs the following steps:

1. Prepare the offline host to redirect requests to the APK repository to the thin client:
    1. Add `127.0.0.1 <apk_repo_host>` to the `/etc/hosts` file
    2. Add an `iptables` rule to redirect requests on port 80 to port 4443 (so you don't need to open the tunnel as `root`, port 80 being protected)
    3. Prepare a `pacman.conf` file containing only the `apk_repo_host`
    4. Open a tunnel to redirect port 4443 on the offline host to port 4666 on the thin client.

2. Open a tunnel to redirect port 4666 from thin client to the APK repository on the online host with: `ssh -R 4666:<apk_repo_host>:80 <online-host>`

_At this point the module can normally use `apk` with `ssh` on the offline host to install the desired packages_

Once the installation has finished, `gui.py` cleans the `/etc/hosts` file and the `iptables` rules from the offline host and closes the SSH tunnels.

Note: when installing each package, `apk` verifies that it has been signed by the authors and maintainers of Alpine Linux. Therefore it is not necessary to trust the online host, but rather to initialise the APK keys in a trusted environment. For users of TowerOS, this means it is imperative to build the TowerOS images in a trusted environment and to manually verify the integrity of the keys.
