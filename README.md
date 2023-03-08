# Tower System Command Line

## Hardware configuration

You must have a thin client (typically a laptop like a Lenovo X270) connected to a switch and one or more Raspberry PI 4 computers connected on the same switch.

## Installation

### 1. With Arch Linux Tower Distribution

The recommended way to use  `tower` tools is to install the Arch Linux Tower Distribution. This distribution contains all the necessary dependencies and is pre-configured so that `tower` tools are directly usable at the first boot.
1. Download the latest image here: ____
2. Use on of the method described here https://wiki.archlinux.org/title/USB_flash_installation_medium to prepare a bootable USB medium.
3. Boot on the USB drive and follow the instruction.

This is the way.

Note: you can build your own image of Tower Distribution with command `build-tower-image thinclient`

### 2. Manually on an Arch Linux distribution

#### 2.1 Install packages

```
$> pacman -S openssh git python python-pip avahi iw wireless_tools base-devel docker archiso
```

#### 2.2 Enable services

```
$> systemctl enable avahi-daemon.service
$> systemctl enable docker.service
$> usermod -aG docker $USER
```

#### 2.3 Install nxagent

```
$> git clone https://aur.archlinux.org/nx.git
$> cd nx
$> makepkg -s -i -r -c
```

#### 2.4 Update sudoers

The `tower` tools assumes that the current user is a "full" sudoers with no password.
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

### 1. Provision a RPI computer

Note: if you are using the Tower Distribution you can skip the first step and use the image in `~/.cache/tower`.

1.1 Generate an image with `build-image`:

```
$> build-tower-image computer
```

This will generate an `img` file compressed with `xz`.

1.2 Use this file to prepare the `sd-card`.

```
$> tower provision <computer-name> --image <image-path-generated-with-build-tower-image>
```

for online host:

```
$> tower provision <computer-name> --online --image <image-path-generated-with-build-tower-image>
```

Keyboard, time zone and wifi parameters are retrieved from the the thin client. You can customize them with the appropriate argument (see `./tower.py provision --help`).

### 2. Execute a command in one of the computer

A terminal command line with `ssh`:

```
$> ssh <computer-name> ls ~/
```

or a graphical appication with `x2go`:

```
$> tower run <computer-name> <application-name>
```

###  3. Install an APT package in one of the computer

```
$> tower install <computer-name> <application-name>
```

or, if the computer is not online

```
$> tower install <offline-computer-name> <application-name> --online-host <online-computer-name> 
```

### 4. List computers and their status

```
$> tower status
```

### 5. Example using two computers

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

## Using with `hatch`

```
$> git clone git@github.com:towercomputing/tools.git
$> cd tools
$> pip install hatch
$> hatch run tower --help
$> hatch run build-tower-image --help
```