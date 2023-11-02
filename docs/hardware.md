TowerOS is designed to run on a thin client device and several hosts connected _via_ one or two unmanaged Ethernet switches. Two switches are necessary if the user would like to have offline as well as online hosts.

The thin client is typically a laptop like the Lenovo X270. The thin client should have an SD card reader for provisioning SD cards that the hosts will boot from. (Raspberry Pi 4Bs may be booted directly from USB, however.) The thin client should also have one or two RJ-45 ports, depending on the number of switches in use.

# Thin Client Hardware Recommendations
- Lenovo X270 Laptop
- Olimex USB Ethernet Adapter (https://www.olimex.com/Products/USB-Modules/USB-GIGABIT/open-source-hardware)
- USB SD Card reader
- 2 Ethernet Cables


# Host Hardware Recommendations
TowerOS currently supports two kinds of host hardware: Raspberry Pi 4B and Compute Module 4 Lite (“CM4” for short). Where as Raspberry Pi 4Bs must be connected with standalone switch hardware, CM4 modules may be connected with a board like the DeskPi Super6C, which provides for a much more compact form factor for a complete TowerOS system. CM4 modules may easily use M.2 SSDs as their persistent storage, _via_ a DeskPi Super6C, and they may therefore perform better.

*Notes*
- The amount of RAM required for each host is heavily dependent on the intended usage pattern. Generally, at least one host should have 8GB of RAM, to run a web browser. For the router host, we recommend having at least 2GB of RAM.
- Different SD cards and USB keys may have very different performance characteristics. In general, USB keys are much faster than SD cards, and M.2 SSDs are faster still.


## Raspberry Pi 4B

![Tower Archi](../img/towerarchi.png)

- Raspberry Pis may be booted either from an SD card or a USB key. For best performance, the root partition should reside on a USB key. You will need at least one SD card or USB key per host.
- The USB key should ideally be plugged into the blue USB port, which supports USB 3.0.
- If you wish to have offline hosts, then you need two switches; otherwise, one will do.
- If you are using a PoE switch, you will need one PoE hat per host; if not, a USB hub may be used for power delivery
- You will need one RJ-45 cable per host.
- You will need one RTC Clock hat for each offline host.


## Compute Module 4 Lite

![DeskPi Super6C Board](../img/deskpi.jpg)

Using CM4s and the [DeskPi Super6C Board](https://deskpi.com/collections/deskpi-super6c/products/deskpi-super6c-raspberry-pi-cm4-cluster-mini-itx-board-6-rpi-cm4-supported) you can avoid most cables and put all your hosts in a single mini-ITX case.

- Only the CM4 *Lite* is supported.
- Only the CM4 Lite module used for the router must have on-board WiFi; the others may be entirely wireless.
- CM4s must be booted from an SD card, which will hold the boot partition.
- CM4s must use an M.2 SSD for the root partition (which also should be highly performant).
- To support both online and offline hosts, two independent DeskPi Super6s may be used.


# Hardware for Debugging
* Monitor
* micro HDMI adapter
* USB Keyboard
* USB Mouse
