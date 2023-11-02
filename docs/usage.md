Hosts are divided into two types: *online* and *offline*. Online hosts live on a separate LAN from offline hosts, and the thin client is connected to both networks. One online host is deemed the “router”, and the router is responsible for providing Internet access to the thin client and all other hosts. If you do not wish to maintain two separate networks, you can simply not provision any offline hosts.

# Provisioning Hosts
TowerOS provides tools for easily provisioning new hosts with the following steps, with the user guided through them by the `tower` CLI tool:

1. Insert an SD card or USB key into the thin client.
2. Call the `$ tower provision` command.
3. Insert the SD card or USB key into the target host hardware.
4. Turn on the host hardware.
5. Wait for the provisioning process to complete on the thin client.

*NOTE:* You must provision a router before you provision any other online hosts.

## Provision the Router
The first online host that you must provision is the router, which connect to the Internet _via_ a WiFi network: 

```
[thinclient]$ tower provision router –wlan-ssid <ssid> –wlan-password <password>
```

## Provision an Online Host
Once the `router` is correctly provisioned, you may provision other online hosts:

```
[thinclient]$ tower provision <host> --online
```

## Provision an Offline Host
An offline host is a host without access to the Internet _via_ the router.

```
[thinclient]$ tower provision <host> --offline
```

# Using TowerOS
Once your hosts are provisioned, you are ready to use TowerOS. You can of course access each host _via_ SSH. However, you can also run GUI applications installed on a host such that the application appears to run on the thin client.

## Execute a command on one of the hosts:

Run a command on a host with SSH:

```
[thinclient]$ ssh <host> <command>
```

## Run a graphical application on a host, with its GUI appearing on the thin client:

```
[thinclient]$ tower run <host> <command>
```

## Install an Alpine package on a host:
TowerOS makes it easy to install new packages on any host by tunneling a connection through the router:

```
[thinclient]$ tower install <host> <package>
```

## List your hosts and their statuses

```
[thinclient]$ tower status
```


# Example Usage

1. Provision the router:

```
[thinclient]$ tower provision router –wlan-ssid <ssid> –wlan-password <password>
```

1. Provision an offline host named `office`:

```
[thinclient]$ tower provision office
```

1. Install GCalculator on the `office` offline host:

```
[thinclient]$ tower install office galculator
```

1. Run galculator `office`:

```
[thinclient]$ startx
[thinclient]$ tower run office gcalculator
```