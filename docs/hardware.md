TowerOS is designed to run on a thin client device and several hosts connected _via_ one or two unmanaged Ethernet switches. Two switches are necessary if the user would like to have offline as well as online hosts.

The thin client is typically a laptop like the Lenovo X270. The thin client should have an SD card reader for provisioning SD cards that the hosts will boot from. (Raspberry Pi 4Bs may be booted directly from USB, however.) The thin client should also have one or two RJ45 ports, depending on the number of switches in use.

TowerOS currently supports two kinds of host hardware: Raspberry Pi 4B and Compute Module 4 Lite.

## 1. Raspberry Pi 4B

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

## 3. Hardware check list

**Thin Client**

- Laptop (Lenovo X270)
- USB Ethernet Adaptater (https://www.olimex.com/Products/USB-Modules/USB-GIGABIT/open-source-hardware)
- SD-Card reader
- 2 RJ45 cables

**Network**

* 2 unmanaged switches

**Rasperry Pi 4b Hosts**

* minimum one RPI for the `router` (2Go RAM recommanded)
* one RPI by host, RAM based and storage storage based on usage pattern
* one SD-Card by host
* one USB Key by host
* one RJ-45 cable by host
* one RTC Clock hat for offline host
* if you are using a POE switch, one POE hat by host or evenetually a USB hub

**Rasperry Pi CM4 Lite**

* One or two Deskpi Super6c board
* minimum one CM4 for the `router` (2Go RAM recommanded)
* one CM4 by host, RAM based and storage storage based on usage pattern
* one SD-Card by host
* one NVMe M.2 SS2 by host

**Suggested for debugging**

* Monitor
* micro HDMI<->monitor cable adapter
* USB keyboard
* USB mouse

