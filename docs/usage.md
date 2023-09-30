## 2. Usage

### 2.1. Provision a host

Note: If you are using TowerOS, you can skip the first step.

#### 2.1.1. Generate an image with build-image

```
$> build-tower-image host
```

This will generate an image file compressed with xz in `~/.cache/tower/builds/`. Images in this folder will be used by default by the provision command if the `--image` flag is not provided.

#### 2.1.2. Prepare the SD card

```
$> tower provision <host> --offline
```

or, for an online host:

```
$> tower provision <host> --online
```

Keyboard, timezone and WiFi parameters are retrieved from the Thin Client. You can customize them with the appropriate argument (see `tower provision --help`).

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

### 2.6. Use with hatch

```
$> git clone git@github.com:towercomputers/tools.git
$> cd tools
$> pip install hatch
$> hatch run tower --help
$> hatch run build-tower-image --help
```

### 2.7. Build a TowerOS image with Docker

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
