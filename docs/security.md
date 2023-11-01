## 1. Security Guarantees

### 1.1 Firewall

- There is zero direct communication between hosts (however there is tunneling for package management).
- All communication between the thin client and a host is over SSH and on port 22 (ideally including screen sharing).
- All communication between the thin client and a host must originate with the thin client.
- No connections to the online hosts may originate from the Internet.
- Tunneling from the thin client to the Internet is allowed.

### 1.2 Hardware

- Online hosts are connected to an Ethernet switch and a WLAN; offline hosts are connected only to the switch.

## 2. Operating System

- Reasonable standards; but this is mostly out of scope. (Disable HT; use a hardened Linux kernel; etc.)

### 2.1. Application-Level

- All network connections between the thin client and a host) must be directly triggered by user action.

## 3. Trusted Computing Base

- Tower Tooling
- Alpine Linux Base System
- Network Drivers
- Network Card Hardware
- SSH
- Screensharing Software

## 4. Threat Analysis

| Class | Attack | Mitigated | If so, how? |
| --- | --- | --- | --- |
| Theft | Theft of Device | Yes | Encrypted root disks |
| Physical Tampering | Evil-Maid Attack | Optional | Raspberry Pis: https://www.zymbit.com/ |
| Physical Tampering | Cold-Boot Attack | Optional | Raspberry Pis: https://www.zymbit.com/ |
| Microarchitectural | RowHammer; RowPress | Yes | Host-Isolation |
| Microarchitectural | Speculative Execution | Yes | Host-Isolation |
| Physical Side-Channel | Power Consumption (https://www.hertzbleed.com/) | Optional | Disable DVFS |
| Physical Side-Channel | Acoustic Emissions | No |  |
| Physical Side-Channel | Electromagnetic Radiation | No |  |