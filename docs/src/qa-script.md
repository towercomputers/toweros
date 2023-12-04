## Manually QA TowerOS

### TowerOS-ThinClient Installation

| Feature | Check | Output |
| ------- | ----- | ------ |
| Fulll Disk Encryption | The USB key containing the `boot` partition must be inserted into the thinclient to boot. | The Thin Client does not start without the USB boot key. |
| Secure Boot | | |
| Welcome Message | A welcome message should indicate the location of the documentation. | |
| Default User | You can log in with the chosen username and password. | |
| Keyboard | Keyboard is correctly configured. | |
| Shell | The shell prompt must be customized. | `[<username>@thinclient <current folder>]$` |
| Partitions | The `swap` partition must be 8Gb, the `home` partition must occupy 20% of the rest, and the `root` partition the remaining space: <br />`[thinclient]$ lsblk` | ![lsblk thinclient](img/lsblk-thinclient.png) |
| Time Zone | `[thinclient]$ date` | The date with the correct time zone. |
| Cron | `supercronic` service must be started:<br />`[thinclient]$ sudo rc-service supercronic status` | `* status: started` |
| Sudo | Default user is sudoer without password:<br />`[thinclient]$ sudo su` | Root session without a password being requested. |
| Documentation | The documentation must be present in the ~/docs folder:<br />`[thinclient]$ ls ~/docs` | List of documents |
| | Documentation can be consulted with `bat`: <br />`[thinclient]$ bat ~/docs/usage.md` | Markdown viewer |
| | Tower CLI man page is installed: <br />`[thinclient]$ man tower` | Tower CLI manual |
| Network | `eth0` must be configured with IP `192.168.2.100`:<br />`[thinclient]$ ip ad` | ![eth0 thinclient](img/eth0-thinclient.png)|
| | `eth1` must be configured with IP `192.168.3.100`:<br />`[thinclient]$ ip ad` | ![eth1 thinclient](img/eth1-thinclient.png)|
| | On reboot the MAC of `eth0` and `eth1` should not change:<br />`[thinclient]$ ip ad` | the value of `link/ether` for `eth0` and `eth1` should not change after a reboot. |
| Firewall | `iptables` service must be started:<br />`[thinclient]$ sudo rc-service iptables status` | `* status: iptables` |
| | Firewal must be correctly configured:<br />`[thinclient]$ sudo iptables -L -v` | [See configuration](https://github.com/towercomputers/toweros/blob/master/tower-lib/toweros-installers/toweros-thinclient/installer/configure-firewall.sh) |
| rfkill | Wifi must be soft blocked:<br />`[thinclient]$ rfkill list wifi` | `Soft blocked: yes` |
| | Bluetooth must be soft blocked:<br />`[thinclient]$ rfkill list bluetooth` | `Soft blocked: yes` |
| Graphical Desktop | `labwc` starts automatically after login if the option was chosen during installation. | |
| | `labwc` should properly start manually:<br />`[thinclient]$ dbus-launch labwc`| |
| | The `sfwbar` menu bar should appear correctly | |
| | `CopyQ` must be correctly started | ![copyq](img/copyq.png) icon in the taskbar |
| | The screen locker should activate correctly after 5 minutes of inactivity | Black screen with password prompt. |
| Tower CLI | The latest version of `tower` cli must be installed:<br />`[thinclient]$ tower version`| Installed version. |

### Hosts provisioning

- The provisioning of the `router`, an online host and an offline host must work correctly.
- The USB key containing the `boot` partition must be inserted into the host to boot.
- `tower status` should display all hosts with status `up`.
- Hosts must be accessible with `ssh` simply with their name (check with `ssh <host>`).
- The default user, keyboard and timezone should be the same as for the thinclient.
- Online hosts must be connected and offline hosts must not (check with `ssh <host> ping www.google.com`).
- The firewall must be correctly configured and activated (`ssh <host> sudo rc-service iptables status` and `ssh <host> iptables -L -v`).
- `eth0` must be configured on the network `192.168.2.0/24` for online hosts and `192.168.3.0/24` for offline hosts (check with `ip ad`).
- On the `router` the MAC of `wlan0` must be different at each startup.
- The `home` partition must occupy 20% and the `root` partition the remaining space. All these partitions must be encrypted. To check, `ssh <host> lsblk` should display something like this:

        NAME         MAJ:MIN RM  SIZE RO TYPE  MOUNTPOINTS
        sda            8:0    1 28.7G  0 disk  
        └─sda1         8:1    1  512M  0 part  
        mmcblk0      179:0    0 29.7G  0 disk  
        └─lvmcrypt   254:0    0 29.7G  0 crypt 
          ├─vg0-home 254:1    0  5.9G  0 lvm   /home
          └─vg0-root 254:2    0 23.8G  0 lvm   /

- `XDG_RUNTIME_DIR` must be set (check with `ssh <host> echo $XDG_RUNTIME_DIR`).
- The shell prompt must be in the form of `[<username>@<host> <current folder>]$` and be of different color for each host.
- Wifi and bluetooth must be soft blocked except wifi in the `router` (check with `ssh <host> rfkill list`).
- Host default user should be able to use sudo without password (check with `ssh <host> sudo su`).
- The hosts should appear in the `labwc` taskbar with a green icon for the 'up' hosts and a red icon for the 'down' hosts (test by turning off one of the hosts)

### Execution and installation of applications

Once the `router` is installed:

- APK packages must be correctly installed on the hosts with `tower install <host> <package>` and on the thinclient with `tower install thinclient <package>`.
- Once installed, graphical applications should appear in the `sfwbar` menu with icons.
- In the menu the applications are classified by host and each host is differentiated by a colored circle.
- For each host the color of the circle is the same as that of the shell prompt (check with `ssh <host>`).
- `ssh <host>` should not display any welcome message.
- Graphical applications can be launched via the `sfwbar` menu or terminal with `tower <host> run <application>`.
- Copy/paste must be possible between two graphics applications running on different hosts.
- Online applications must work correctly on online hosts (check for example that it is possible to browse the web with Midori).
- The `tor` proxy must be accessible from online hosts (check with `ssh web curl --socks5 192.168.2.1:9050 https://check.torproject.org/api/ip`).
- The time on online hosts must be correct (thanks to `chronyd`).

### TowerOS-ThinClient Upgrade

In addition to all the points listed for installing TowerOS-ThinClient:

- The new version of `tower` cli must be installed (check with `tower version`).
- All previously installed hosts must be accessible (check with `tower status`).
- The `sfwbar` menu must display all applications previously installed on the hosts.
- The `sfwbar` widget indicating the host status must be active.
- The contents of the home partition must be completely preserved.

### Host Upgrade

In addition to all the points listed for Hosts provisioning:

- The new version of TowerOS-Host must be installed (check with `tower status`).
- All applications installed with `tower install` must be reinstalled.
- The contents of the host home partition must be completely preserved.
