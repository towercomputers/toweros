# Installation

To use TowerOS, you must first install the image for the thin client on the device you wish to use (normally a laptop):

1. Download the latest image here: [https://github.com/towercomputers/toweros/releases/latest](https://github.com/towercomputers/toweros/releases/latest).
2. Prepare a bootable USB medium using the above image.
3. Boot the thin client with the USB drive and follow the instructions.

# Update

1. Update TowerOS-Thinclient

To update the Thin Client you must proceed in exactly the same way as for the installation and select "Update TowerOS-Thinclient" in the first question.

During an update the system is completely reinstalled. Only the /home folder with hosts configurations and keys are kept. If you have data outside of /home, make sure to make a backup before starting the update.

2. Update hosts

    [thinclient]$ tower update <hostname>

During an update the system is completely reinstalled. Only the /home folder is kept. If you have data outside of /home, make sure to make a backup before starting the update.
Once the system is updated, all applications installed with `tower install <hostname>` are automatically re-installed.
Note: Start by updating the `router` and then the other hosts.