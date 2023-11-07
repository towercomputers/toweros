## Security Model

- Direct communication between hosts is forbidden.
- Incoming connections to the thin client are forbidden.
- All communication with a host must originate with the thin client and be:
	- over SSH,
	- on port 22, and
	- *via* Ethernet.
- All communication between the thin client and a host must be directly triggered by user action.
- SSH tunnels from the thin client or an online host to the Internet, through the router, are allowed.


## Operating System
In general, operating system configuration is outside the scope of TowerOS's responsibilities; TowerOS does attempt to be *secure by default*, however. Of course, the core architecture of TowerOS is designed to mitigate the severity of any compromise of a host. For information on how best to securing your thin client and hosts at the level of the operating system, please see this [Linux Hardening Guide](https://madaidans-insecurities.github.io/guides/linux-hardening.html).


## Trusted Computing Base

- TowerOS Tooling
- Alpine Linux Base System
- Network Drivers
- Network Card Hardware
- SSH
- NX (Screensharing)


## Threat Analysis

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
