# Tower System Command Line

## Installation

1. Install requirements

Arch Linux is required.

1.1 Install packages

```
$> pacman -S openssh git python python-pip avahi iw wireless_tools base-devel docker
```

1.2 Enable services

```
$> systemctl enable avahi-daemon.service
$> systemctl enable docker.service
$> usermod -aG docker $USER
```

1.3 Install nxagent

```
$> git clone https://aur.archlinux.org/nx.git
$> cd nx
$> makepkg -s -i -r -c
```

1.4 Eventually install a graphical desktop to use `x2go`:

```
$> pacman -S lxkde xorg-xinit
$> echo "exec startlxde" > /home/tower/.xinitrc
$> startx
```

2. Update sudoers

The script assumes that the current user is a "full" sudoers with no password.
Check if `/etc/sudoers` contains the following line:

```
<you_username> ALL=(ALL) NOPASSWD: ALL
```

3. Install `tower`

Update `pip` to the latest version:

```
$> python3 -m pip install --upgrade pip
```

then:

```
$> python3 -m pip install "tower-tools @ git+ssh://github.com/towercomputing/tools.git"
```

## Usage

### Provision an host

1. Generate an image with `build-image`:

```
$> build-tower-image
```

This will generate an `img` file compressed with `xz`.

2. Use this file to prepare the `sd-card`.

```
$> tower provision <computer-name> --image <image-path-generated-with-build-tower-image>
```

for online host:

```
$> tower provision <computer-name> --online --image <image-path-generated-with-build-tower-image>
```

Keyboard, time zone and wifi parameters are retrieved from the the thin client. You can customize them with the
appropriate argument (see `./tower.py provision --help`).

### Execute a command in one of the host

A terminal command line with `ssh`:

```
$> ssh <computer-name> ls ~/
```

or a graphical appication with `x2go`:

```
$> tower run <computer-name> thunderbird
```

### Install an APT package in one of the host

```
$> tower install <computer-name> thunderbird
```

or, if the host is not online

```
$> tower install <offline-computer-name> thunderbird --online-host <online-computer-name> 
```

### List hosts and their status

```
$> tower status
```

## Using with `hatch`

```
$> git clone git@github.com:towercomputing/tools.git
$> cd tools
$> pip install hatch
$> hatch run tower --help
$> hatch run build-tower-image --help
```