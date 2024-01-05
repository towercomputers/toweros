# TowerOS Installation

## Thin Client Installation

To use TowerOS, you must first install the image for the thin client on the device you wish to use (normally a laptop):

1. Download the latest installation image from the **[TowerOS GitHub releases page](https://github.com/towercomputers/toweros/releases/latest)**.
2. Prepare a bootable USB medium using the above image.
3. Boot the thin client with the USB device and follow the on-screen instructions.

## Provisioning Hosts
Hosts are divided into two types: *online* and *offline*. Online hosts live on a separate LAN from offline hosts, and the thin client is connected to both networks. One online host is identified as the “router”, and the router is responsible for providing Internet access to the thin client and all other hosts. If you do not wish to maintain two separate networks, you can simply not provision any offline hosts.

TowerOS provides tools for easily provisioning new hosts with the following steps, with the user guided through them by the `tower` CLI tool:


*Note:* You must provision a router before you provision any other online hosts.

*Note:* It is a good idea to reserve one (offline) host for managing removable storage (esp. when using the DeskPi Super6C and CM4s, since then only one host has its USB ports exposed).


### Router
The first online host that you must provision is the router, which connects to the Internet _via_ a WiFi network: 

1. Insert the root device (SD card or USB key for RPI, M.2 SSD for CM4) into the *host device*.
2. Insert the boot device (SD card or USB key for RPI, SD card for CM4) into the *thin client*.
3. Run `[thinclient]$ tower provision router –wlan-ssid <ssid> –wlan-password <password>` to prepare the host boot device.
4. Remove the boot device from the thin client and insert it into the target host device.
5. Turn on the host device.
6. Wait for the provisioning process to complete (on the thin client).

### Online Hosts
Once the `router` is correctly provisioned, you may provision other online hosts by following the same steps as above, but using the following command for step 3:

```
[thinclient]$ tower provision <host> --online`
```


### Offline Hosts (Optional)
An offline host is a host without access to the Internet _via_ the router. Offline hosts are provisioned in the same way as online hosts, except you must pass the `--offline` argument to the `tower provision` command. Offline hosts must be connected to a separate network from the online hosts.


### Troubleshooting

Sometimes a host fails to come up during the provisioning process, and you are left waiting on the thin client for the provisioning process to finish. If the host is not accessible _via_ `[thinclient]$ ssh <host>`, the most likely problem is in the networking. The following is a list of checks to perform in this case:

1. With `[thinclient]$ ip ad`, check that the interface `eth0` is UP, with the IP `192.168.2.100`, and that the interface `eth1` is UP with the IP `192.168.3.100`.
1. Check that the thin client is connected to the online switch with `eth0` and to the offline switch with `eth1`.
1. Check that the host is connected to the correct switch.
1. Check that the host is visible with `[thinclient]$ nmap -sn 192.168.2.0/24` for an online host and `nmap -sn 192.168.3.0/24` for an offline host.

If all of these checks are OK and you still cannot access the host, you must connect a screen and keyboard to the host and look for error messages that appear during the boot process.


## Thin Client Upgrades

To upgrade the Thin Client use the following command:

```
[thinclient]$ tower upgrade
```

During an upgrade the system is completely reinstalled. Only the `/home` folder, which contains the TowerOS configuration and keys is kept.
Before starting the upgrade, make sure that:

- If you have data outside of thinclient and/or hosts `/home`, make sure to make a backup.
- That all hosts are turned on with their own boot devices inserted.

## Host Upgrades

The hosts are automatically updated at the end of the Thin Client upgrade. You can also manually upgrade them with:

```
[thinclient]$ tower upgrade --hosts
```

or upgrade only some hosts with:

```
[thinclient]$ tower upgrade --hosts <host1> <host2> ...
```

During an upgrade the system is completely reinstalled; only the `/home` folder is kept. If you have data stored on the host outside of `/home`, make sure to make a backup before starting the upgrade.
  
Once the system has been upgraded, all applications installed with `tower install <host>` are automatically re-installed.
