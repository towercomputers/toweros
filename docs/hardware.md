To use Tower you need a Thin Client and several Hosts connected via one or ideally two switches.

The Thin Client is typically a laptop like the Lenovo X270. An SD-card reader is necessary for the Thin Client to prepare the SD-cards containing the hosts' OS. Two RJ45 ports are also necessary to connect the Thin Client to the two switches (you can optionally use a USB ethernet adapter).

For the moment tower has been tested with two types of hosts: Raspberry PI 4b and Compute Module 4 Lite.

## 1. Raspberry PI 4b

![Tower Archi](../img/towerarchi.png)

For each Raspberry PI you need:

- an SD card, for the boot partition
- a USB key which will serve as a hard drive.
- for offline hosts a Real Time Clock hat

Tips:

- Remember to plug the USB key into the blue port (USB 3.0)
- For hosts that serve as a router we recommend an RPI with 2GB of RAM, for others, especially if you plan to run graphicals applications, we recommend 8GB of RAM.
- for sd-cards and usb keys, look at the list of hardware that we tested and their performance (TODO)

## 2. Compute Module 4 Lite

![Deskpi Super6c board](../img/deskpi.jpg)

Using CM4s and the [Deskpi Super6c board](https://deskpi.com/collections/deskpi-super6c/products/deskpi-super6c-raspberry-pi-cm4-cluster-mini-itx-board-6-rpi-cm4-supported) you can avoid most cables and put all your hosts in an ATX case.

For each CM4 you need:

- an SD card, for the boot partition
- a NVMe M.2 SS2 which will serve as a hard drive.

One of the CM4s, the one that will serve as a router, must have WiFi and 2GB of RAM is sufficient. For other hosts, WiFi is not necessary, but we recommend 8GB of RAM, especially for hosts that need to run graphicals applications.

Ideally you should use two Deskpis, one for online hosts and another for offline hosts.
