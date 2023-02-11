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

## Usage


```
$> ./tower.py <command> --help
```

Commands `provision`, `install`, `run` or `list`

