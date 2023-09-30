## 3. Implementation

To date, `tower-tools` includes six main modules: `buildthinclient.py` and `buildhost.py` to build the OS images used by the `thinclient` and the hosts. `sshconf.py` which manages `tower-tools` and `ssh` configuration files. `provision.py`, `install.py`, and `gui.py` which respectively allow you to provision a host, to install an application on it even without an internet connection and to run a graphical application of a host from the `thinclient`.

### 3.1. TowerOS-ThinClient

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

**Notes about the TowerOS-ThinClient installer:**

* The TowerOS-ThinClient install scripts generally follow the official Alpine Linux install guide (see [https://wiki.alpinelinux.org/wiki/Installation](https://wiki.alpinelinux.org/wiki/Installation)) 
* The installer sets up an `iptables` firewall as described here [https://wiki.archlinux.org/title/Simple_stateful_firewall](https://wiki.archlinux.org/title/Simple_stateful_firewall).
* TowerOS-ThinClient uses `Syslinux` as the boot loader.


### 3.2. TowerOS-Host

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

### 3.3. SSHConf

`tower-tools` uses a single configuration file in the same format as an SSH config file: `~/.ssh/tower.conf`. This file, included in `~/.ssh/config`, is used both by `tower-tools` to maintain the list of hosts and by `ssh` to access hosts directly with `ssh <host>`. `sshconf.py` is responsible for maintaining this file and generally anything that requires manipulation of something in the `~./ssh` folder. Notably:

1. to discover the IP of a newly installed host and update `tower.conf`
2. update `~/.ssh/know_hosts`
3. check the status of a host and if he is online.

Note: `sshconf.py` uses [https://pypi.org/project/sshconf/](https://pypi.org/project/sshconf/) to manipulate `ssh` config files.

### 3.4. Provision

`provision.py` is used by the `tower provision <host>` command to prepare an SD card directly usable by a Rasbperry PI.

The steps to provision a host are as follows:

1. generation of a key pair.
2. generation of the host configuration (`tower.env` file), with the values provided on the command line, or with those retrieved from the `thinclient`.
3. copy of the TowerOS-ThinClient image on the SD card and insertion of the configuration file.
4. waiting for the new host to be detected on the network after the user inserts the sd-card in the RPI and the boot is finished.
5. updated `ssh` and `tower-tools` configuration file.

Once a host is provisioned it is therefore directly accessible by ssh with `ssh <host>` or `tower run <host>`.

### 3.5. GUI

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

### 3.6. Install

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
