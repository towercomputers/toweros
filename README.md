# Tower System Command Line

## Hardware configuration

You must have a thin client (typically a laptop like a Lenovo X270) connected to a switch and one or more Raspberry PI 4 computers connected on the same switch.

## Installation

### 1. TowerOS Thin Client

The easiest way to use Tower is to run the TowerOS GNU/Linux distribution (based on Arch Linux) on your Thin Client.

#### To install TowerOS on your Thin Client:
1. Download the latest image here: ____
2. Prepare a bootable USB medium using the above image.
3. Boot the Thin Client the USB drive and follow the instructions.

Note: you can build your own image of the TowerOS installer with command `build-tower-image thinclient`.

### 2. Custom Thin-Client (Linux)

#### 2.1 Install packages

##### 2.1.1 from Arch Linux
```
$> pacman -S openssh git python python-pip avahi iw wireless_tools base-devel docker archiso
```

#### 2.2 Enable services

```
$> systemctl enable avahi-daemon.service
$> systemctl enable docker.service
$> usermod -aG docker $USER
```

#### 2.3 Install `nxagent`

```
$> git clone https://aur.archlinux.org/nx.git
$> cd nx
$> makepkg -s -i -r -c
```

#### 2.4 Update `/etc/sudoers`

The `tower` tools assumes that the current user has full `sudo` access, with no password. (Please refer to our *threat model*.)
Check if `/etc/sudoers` contains the following line:

```
<you_username> ALL=(ALL) NOPASSWD: ALL
```

#### 2.5. Install `tower`

Update `pip` to the latest version:

```
$> python3 -m pip install --upgrade pip
```

then:

```
$> python3 -m pip install "tower-tools @ git+ssh://github.com/towercomputing/tools.git"
```

## Usage

### 1. Provision a Host

Note: if you are using TowerOS, you can skip the first step and use the image in `~/.cache/tower`.

1.1 Generate an image with `build-image`:

```
$> build-tower-image computer
```

This will generate an `img` file compressed with `xz`.

1.2 Use this file to prepare the SD card.

```
$> tower provision <computer-name> --image <image-path-generated-with-build-tower-image>
```

or, for an online host:

```
$> tower provision <computer-name> --online --image <image-path-generated-with-build-tower-image>
```

Keyboard, timezone and WiFi parameters are retrieved from the the thin client. You can customize them with the appropriate argument (see `./tower.py provision --help`).

### 2. Execute a command on one of the computers:

A terminal command line with SSH:

```
$> ssh <computer-name> ls ~/
```

or a graphical application with `x2go`:

```
$> tower run <computer-name> <application-name>
```

###  3. Install an APT package on one of the hosts:

```
$> tower install <computer-name> <application-name>
```

or, if the host is offline, you can tunnel the installation through an online host:

```
$> tower install <offline-computer-name> <application-name> --online-host <online-computer-name> 
```

### 4. List computers and their status:

```
$> tower status
```

### 5. Example using two hosts:

provision a first offline computer named `office`

```
$> tower provision office --image=/home/tower/.cache/Raspbian-tower-20230306141627.img.xz
```

provision a second online computer named `web`

```
$> tower provision web --online --image=/home/tower/.cache/Raspbian-tower-20230306141627.img
```

install `galculator` in `office` computer

```
$> tower install office galculator --online-host=web
```

run `galculator` from `office`

```
$> startx
$> tower run office galculator
```

## Use with `hatch`

```
$> git clone git@github.com:towercomputing/tools.git
$> cd tools
$> pip install hatch
$> hatch run tower --help
$> hatch run build-tower-image --help
```
