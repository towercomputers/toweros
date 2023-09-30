# Tower

**Tower** is a computer system for paranoid individuals and high-value targets that turns the existing paradigm for computer security on its head: Instead of taking a single computer and splitting it into multiple security domains at the level of the operating system or hypervisor (cf. [AppArmor](https://apparmor.net/) and [QubesOS](https://www.qubes-os.org/)), Tower combines *multiple, independent computers* into a single, unified, virtual system with a shared, composited user interface. Each security domain is regelated to a separate, dedicated *Host* (e.g. a Raspberry Pi), and the user accesses their applications from a *Thin Client* (e.g. a laptop) over a LAN using standard network protocols (namely, SSH and NX), following strict firewall rules that govern all network communication.

Technically speaking, Tower is an example of a *converged multi-level secure (MLS) computing system*. In contrast to existing designs, Tower offers theoretically greater security guarantees, better usability, and more flexibility. The downside, of course, is that you need multiple computers to make it work. But with the development of cheap, powerful and small single-board computers (SBCs), it's now quite practical to carry half a dozen computers with you wherever you go. So, instead of having to trust your operating system or hypervisor to be able properly to isolate different security domains all running on shared hardware, you can rely on standard, open-source implementations of widely used networking protocols, to connect multiple independent computers together to form a single, virtual device that functions very much like a normal desktop or laptop.

This repository represents an OSS implementation of the above design. It includes within it tools for the following purposes:

1. Provisioning and maintaining the Thin Client
2. Provisioning, maintaining and monitoring the various Hosts
3. Managing the network layer (provisioning the Switch, enforcing firewall rules, etc.)

For a more formal description of the Tower architecture, including a comparison with Qubes OS, please refer to [the whitepaper](Tower%20Whitepaper.pdf).


* 1.[ Installation](installation.md#1-installation)
  * 1.1. [Hardware configuration](installation.md#11-hardware-configuration)
  * 1.2. [TowerOS-ThinClient](installation.md#12-toweros-thin-client)
  * 1.3. [Custom Thin Client (Linux)](installation.md#13-custom-thin-client-linux)
    * 1.3.1. [Install dependencies](installation.md#131-install-dependencies)
    * 1.3.2. [Enable services](installation.md#132-enable-services)
    * 1.3.3. [Update /etc/sudoers](installation.md#134-update-etcsudoers)
    * 1.3.4. [Install `tower-tools`](installation.md#135-install-tower-tools)
* 2.[ Usage](usage.md#2-usage)
  * 2.1. [Provision a Host](usage.md#21-provision-a-host)
    * 2.1.1. [Generate an image with build-image](usage.md#211-generate-an-image-with-build-image)
    * 2.1.2. [Prepare the SD card](usage.md#212-prepare-the-sd-card)
  * 2.2. [Execute a command in one of the hosts](usage.md#22-execute-a-command-in-one-of-the-hosts)
  * 2.3. [Install an application on one of the hosts](usage.md#23-install-an-application-on-one-of-the-hosts)
  * 2.4. [List hosts and their status](usage.md#24-list-hosts-and-their-status)
  * 2.5. [Example using two hosts](usage.md#25-example-using-two-hosts)
  * 2.6. [Use with hatch](usage.md#26-use-with-hatch)
  * 2.7. [Build a TowerOS image with Docker](usage.md#27-build-a-toweros-image-with-docker)
* 3.[ Implementation](implementation.md#3-implementation)
  * 3.1. [TowerOS-ThinClient](implementation.md#31-toweros-thinclient)
  * 3.2. [TowerOS-Host](implementation.md#32-toweros-host)
  * 3.3. [SSHConf](implementation.md#33-sshconf)
  * 3.4. [Provision](implementation.md#34-provision)
  * 3.5. [GUI](implementation.md#35-gui)
  * 3.6. [Install](implementation.md#36-install)
