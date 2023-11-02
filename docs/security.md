## Security Model

- Direct communication between Hosts is forbidden.
- All communication between the Thin Client and a Host is over SSH and on port 22.
- All communication with a Host must originate with the Thin Client.
- All network connections between the Thin Client and a Host must be directly triggered by user action.
- SSH tunnels from the Thin Client or a Host through the Router are allowed.

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