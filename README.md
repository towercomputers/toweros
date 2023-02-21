# Tower System Command Line

## Installation

1. Install requirements

- Linux platform only
- Python >= 3.9
- `nxproxy` to run an application with x2go (`sudo apt-get install nxproxy`)
- Docker (only if you need to build an image)

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