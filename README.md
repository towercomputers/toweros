# Tower System Command Line

## Installation on Linux platform

1. Install `python-x2go` and `nxproxy`

```
$> wget https://code.x2go.org/releases/source/python-x2go/python-x2go-0.6.1.3.tar.gz
$> tar -xf python-x2go-0.6.1.3.tar.gz
$> cd python-x2go-0.6.1.3
$> sudo python setup.py install
$> sudo apt-get install nxproxy
```

2. Install other requirements

```
$> pip install -r requirements.txt
```

## Provision an host

```
$> ./tower.py provision office
```

for online host:

```
$> ./tower.py provision web --online
```

Keyboard, time zone and wifi parameters are retrieved from the the thin client. You can customize them with the
appropriate argument (see `./tower.py provision --help`).

## Execute a command in one of the host

With `ssh`:

```
$> ssh office ls Dowloads
```

With `x2go`:

```
$> ./tower.py run office thunderbird
```

## Install a package in one of the host

```
$> ./tower.py install office thunderbird
```

or, if the host is not online

```
$> ./tower.py install office thunderbird --online-host web
```

## List hosts

```
$> ./tower.py list
```