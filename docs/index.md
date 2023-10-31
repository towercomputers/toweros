# Tower

**Tower** is a computer system for paranoid individuals and high-value targets that turns the existing paradigm for computer security on its head: Instead of taking a single computer and splitting it into multiple security domains at the level of the operating system or hypervisor (cf. [AppArmor](https://apparmor.net/) and [QubesOS](https://www.qubes-os.org/)), Tower combines *multiple, independent computers* into a single, unified, virtual system with a shared, composited user interface. Each security domain is regelated to a separate, dedicated *Host* (e.g. a Raspberry Pi), and the user accesses their applications from a *Thin Client* (e.g. a laptop) over a LAN using standard network protocols (namely, SSH and NX), following strict firewall rules that govern all network communication.

Technically speaking, Tower is an example of a *converged multi-level secure (MLS) computing system*. In contrast to existing designs, Tower offers theoretically greater security guarantees, better usability, and more flexibility. The downside, of course, is that you need multiple computers to make it work. But with the development of cheap, powerful and small single-board computers (SBCs), it's now quite practical to carry half a dozen computers with you wherever you go. So, instead of having to trust your operating system or hypervisor to be able properly to isolate different security domains all running on shared hardware, you can rely on standard, open-source implementations of widely used networking protocols, to connect multiple independent computers together to form a single, virtual device that functions very much like a normal desktop or laptop.

This repository represents an OSS implementation of the above design. It includes within it tools for the following purposes:

1. Provisioning and maintaining the Thin Client
2. Provisioning, maintaining and monitoring the various Hosts
3. Managing the network layer (provisioning the Switch, enforcing firewall rules, etc.)

For a more formal description of the Tower architecture, including a comparison with Qubes OS, please refer to [the whitepaper](Tower%20Whitepaper.pdf).

