# Tower System Command Line

```
$> ./tower.py --help
usage: tower.py [-h] {provision,install,run,list} ...

Tower Computing command line. Provision a computer with the `provision` command then install on it an application with `install` and
finally run the applications with the `run` command. Use `./tower {provision|install|run} --help` to get options list for each
command.

positional arguments:
  {provision,install,run,list}
    provision           Command used to prepare the bootable SD Card needed to provision a computer.
    install             Command used to install an application in a computer prepared with the `provision` command.
    run                 Command used to run an application prepared with `install` command.
    list                List all the computers and applications.

options:
  -h, --help            show this help message and exit
```

## Provision

```
$> ./tower.py provision --help
usage: tower.py provision [-h] -n NAME -sd SD_CARD [--host HOST] [--netmask NETMASK] [--public-key PUBLIC_KEY]
                          [--private-key PRIVATE_KEY] [--config-dir CONFIG_DIR]

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Computer's name. This name is used to install and run an application (Required).
  -sd SD_CARD, --sd-card SD_CARD
                        SD Card path (Required).
  --host HOST           IP or domain name of the application computer (Default: randomly generated).
  --netmask NETMASK     Netmask of the application computer (Default: 255.255.255.0).
  --public-key PUBLIC_KEY
                        Public key path used to access the application computer (Default: automatically generated and stored in the
                        SD card and the local ~/.ssh/ folder).
  --private-key PRIVATE_KEY
                        Private key path used to access the application computer (Default: automatically generated and stored in the
                        local ~/.ssh/ folder).
  --config-dir CONFIG_DIR
                        Directory where the config file for this computer will be placed (Default: ~/.config/tower/).
```

## Install

```
$> ./tower.py install --help
usage: tower.py install [-h] -n NAME -p PATH -a ALIAS [--apt-packages APT_PACKAGES] [--local-apt-packages LOCAL_APT_PACKAGES]
                        [--config-dir CONFIG_DIR]

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Computer's name where to install the application. A config file MUST exists for this name (Required).
  -p PATH, --path PATH  Application's binary path in the application computer (Required).
  -a ALIAS, --alias ALIAS
                        Name used to run the application (Required).
  --apt-packages APT_PACKAGES
                        Comma separated list of apt packages to install in th SD Card (Default: assume the application is already
                        installed).
  --local-apt-packages LOCAL_APT_PACKAGES
                        Comma separated list of apt packages local file pathes to install in th SD Card. (Default: assume the
                        application is already installed)
  --config-dir CONFIG_DIR
                        Directory where the config file for this computer will be placed (Default: ~/.config/tower/).
```

## Run

```
$> ./tower.py run --help
usage: tower.py run [-h] -n NAME -a ALIAS [-c CONFIG_DIR]

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Computer's name. This name must match with the `name` used with the `provision` command (Required).
  -a ALIAS, --alias ALIAS
                        Application's alias. This name must match with the `alias` used with the `install` command (Required).
  -c CONFIG_DIR, --config-dir CONFIG_DIR
                        Directory where the config file for this appication is placed (Default: ~/.config/ts/).
```

## List

```
$> ./tower.py list --help
usage: tower.py list [-h] [-n NAME] [-c CONFIG_DIR]

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  List only the applications installed in the given computer (Default: none).
  -c CONFIG_DIR, --config-dir CONFIG_DIR
                        Directory config files are placed (Default: ~/.config/ts/).
```