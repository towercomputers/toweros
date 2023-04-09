# Tower System Command Line

## Hardware configuration

You must have a Thin Client (typically a laptop like a Lenovo X270) connected to a switch and one or more Raspberry PI 4 computers connected on the same switch.

## Installation

### 1. TowerOS Thin Client

The easiest way to use Tower is to run the TowerOS GNU/Linux distribution (based on Arch Linux) on your Thin Client.

#### To install get TowerOS:
1. Download the latest image here: ____
2. Prepare a bootable USB medium using the above image.
3. Boot the Thin Client the USB drive and follow the instruction.

Note: you can build your own image of TowerOS with command `build-tower-image thinclient` or with Docker (see below).

### 2. Custom Thin-Client (Linux)

#### 2.1 Install packages

##### 2.1.1 from Arch Linux
```
$> pacman -S openssh git python python-pip avahi iwd base-devel docker archiso
```

#### 2.2 Enable services

```
$> systemctl enable avahi-daemon.service
```

#### 2.3 Install `nxproxy`

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
$> python3 -m pip install "tower-tools @ git+ssh://github.com/towercomputers/tools.git"
```

## Usage

### 1. Provision a Host

Note: if you are using TowerOS, you can skip the first step.

1.1 Generate an image with `build-image`:

```
$> build-tower-image host
```

This will generate an `img` file compressed with `xz` in `~/.cache/tower/builds/`.
Images in this folder will be used by default by the `provision` command if the `--image` flag is not provided.

1.2 Prepare the SD card.

```
$> tower provision <host> 
```

or, for an online host:

```
$> tower provision <host> --online
```

Keyboard, timezone and WiFi parameters are retrieved from the the Thin Client. You can customize them with the appropriate argument (see `./tower.py provision --help`).


### 2. Execute a command in one of the hosts

A terminal command line with SSH:

```
$> ssh <host> ls ~/
```

or a graphical application with `NX` protocol:

```
$> tower run <host> <application-name>
```

###  3. Install an APT package on one of the hosts:

```
$> tower install <host> <application-name>
```

or, if the host is offline, you can tunnel the installation through an online host:

```
$> tower install <offline-host> <application-name> --online-host <online-host> 
```

### 4. List hosts and their status:

```
$> tower status
```

### 5. Example using two hosts:

provision a first offline host named `office`

```
$> tower provision office --image=/home/tower/.cache/Raspbian-tower-20230306141627.img.xz
```

provision a second online host named `web`

```
$> tower provision web --online --image=/home/tower/.cache/Raspbian-tower-20230306141627.img
```

install `galculator` in `office` host

```
$> tower install office galculator --online-host=web
```

run `galculator` from `office`

```
$> tower run office galculator
```

## Use with `hatch`

```
$> git clone git@github.com:towercomputers/tools.git
$> cd tools
$> pip install hatch
$> hatch run tower --help
$> hatch run build-tower-image --help
```

## Build a TowerOS image with Docker.

1. Build the Docker image with:

```
$> docker build -t build-tower-image:latest .
```

2. Build the TowerOS image inside a Docker container:

```
$> docker run --name towerbuilder --user tower --privileged \
               build-tower-image thinclient
```

3. Retrieve that image from the container:

```
$> docker cp towerbuilder:/home/tower/toweros-20230318154719-x86_64.iso ./
```

Note: With the ARM64 architecture, you must use `buildx` and a cross-platform emulator like `tonistiigi/binfmt`.

```
$> docker buildx create --use
$> docker buildx build -t build-tower-image:latest --platform=linux/amd64 --output type=docker .
$> docker run --privileged --rm tonistiigi/binfmt --install all
$> docker run --platform=linux/amd64 --name towerbuilder --user tower --privileged \
              build-tower-image thinclient
```
