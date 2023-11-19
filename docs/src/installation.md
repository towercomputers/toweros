## Installation

To use TowerOS, you must first install the image for the thin client on the device you wish to use (normally a laptop):

1. Download the latest image here: [https://github.com/towercomputers/toweros/releases/latest](https://github.com/towercomputers/toweros/releases/latest).
2. Prepare a bootable USB medium using the above image.
3. Boot the thin client with the USB drive and follow the instructions.

## Upgrade

1. Update TowerOS-Thinclient

    To update the Thin Client you must proceed in exactly the same way as for the installation and select "Update TowerOS-Thinclient" in the first question.

    During an update the system is completely reinstalled. Only the /home folder with hosts configurations and keys are kept. If you have data outside of /home, make sure to make a backup before starting the update.

2. Update hosts

        [thinclient]$ tower update <host>

    During an update the system is completely reinstalled. Only the /home folder is kept. If you have data outside of /home, make sure to make a backup before starting the update.
    Once the system is updated, all applications installed with `tower install <host>` are automatically re-installed.
    Note: Start by updating the `router` and then the other hosts.

## Troubleshooting

In case a host is not accessible:

- either by the provisioning script
- either with `ssh <host>`
- either appears as "down" with `tower status`

The most likely cause is a network problem. Here is the list of checks to carry out:

1. With `ip ad` check that the interface `eth0` is UP and with the ip `192.168.2.100` and that the interface `eth1` is UP with the ip `192.168.3.100`.
1. check that the Thin Client is connected to the online switch with `eth0` and to the offline switch with `eth1`.
1. check that the host is connected to the correct switch
1. check that the host is visible with `nmap -sn 192.168.2.0/24` for an online host and `nmap -sn 192.168.3.0/24` for an offline host.

If all of these checks are ok and you still cannot access the host, you must connect a screen and keyboard to the host and check for any error messages.