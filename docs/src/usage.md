# Using TowerOS
Once your [hosts have been provisioned](installation.md#Provisioning Hosts), you are ready to use TowerOS. You can of course access each host _via_ SSH. However, you can also run GUI applications installed on a host such that the application appears to run on the thin client.

## Execute a command on one of the hosts

Run a command on a host with SSH:

```
[thinclient]$ ssh <host> <command>
```

## Run a graphical application on a host, with its GUI appearing on the thin client

```
[thinclient]$ tower run <host> <command>
```

## Install an Alpine package on a host
TowerOS makes it easy to install new packages on any host by tunneling a connection through the router:

```
[thinclient]$ tower install <host> <package>
```

## List your hosts and their statuses

```
[thinclient]$ tower status
```

## Get thin client and host versions

```
[thinclient]$ tower version
```

## Update `router` wifi credentials

```
[thinclient]$ tower wlan-connect --ssid <ssid> --password <password>
```

## Configure wallpaper, screen lock timeout and desktop auto start

Edit the file `~/.local/tower/osconfig` with the following variables:

```
LOCK_SCREEN_AFTER=300 # 5 minutes
WALLPAPER_IMAGE=/var/towercomputers/wallpaper.jpg
STARTW_ON_LOGIN='false'
```
