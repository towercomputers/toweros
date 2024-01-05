<!--Do not edit manually. Generated with `[tower-cli]$ hatch run tower mdhelp > ../docs/src/manual.md`.-->
## NAME
<div style="margin:0 50px">tower</div>
## SYNOPSIS
<div style="margin:0 50px; font-family:Courier">tower [-h] [--quiet] [--verbose] {provision,upgrade,install,run,status,wlan-connect,version}} ...</div>
## DESCRIPTION
<div style="margin:0 50px">TowerOS command-line interface for provisioning hosts, install APK packages on it and run applications with NX protocol.</div>
## COMMANDS
<div style="margin:0 50px">
<b>tower</b> <u><a href="#tower-provision">provision</a></u><br /><div style="margin:0 50px">Prepare the bootable device needed to provision a host</div><br />
<b>tower</b> <u><a href="#tower-upgrade">upgrade</a></u><br /><div style="margin:0 50px">Prepare the bootable device needed to upgrade a host</div><br />
<b>tower</b> <u><a href="#tower-install">install</a></u><br /><div style="margin:0 50px">Install an application on a host with APK</div><br />
<b>tower</b> <u><a href="#tower-run">run</a></u><br /><div style="margin:0 50px">Run an application on the specified host, with the GUI on the thin client.</div><br />
<b>tower</b> <u><a href="#tower-status">status</a></u><br /><div style="margin:0 50px">Check the status of all hosts in the Tower system.</div><br />
<b>tower</b> <u><a href="#tower-wlan-connect">wlan-connect</a></u><br /><div style="margin:0 50px">Update WiFi credentials on the router.</div><br />
<b>tower</b> <u><a href="#tower-version">version</a></u><br /><div style="margin:0 50px">Get the version of TowerOS installed on the thin client and hosts.</div><br />
<b>tower</b> <u><a href="#tower-poweroff">poweroff</a></u><br /><div style="margin:0 50px">Poweroff all hosts.</div><br />
<b>tower</b> <u><a href="#tower-deprovision">deprovision</a></u><br /><div style="margin:0 50px">Deprovision a host.</div><br />
</div>
### `tower provision`
<div style="margin:0 50px; font-family:Courier">usage: tower provision [-h] [--boot-device BOOT_DEVICE] [--zero-device] [--no-confirm] [--image IMAGE] [--ifname IFNAME] [--no-wait] [--timeout TIMEOUT] [--force] [--public-key-path PUBLIC_KEY_PATH] [--private-key-path PRIVATE_KEY_PATH] [--password PASSWORD] [--keyboard-layout KEYBOARD_LAYOUT] [--keyboard-variant KEYBOARD_VARIANT] [--timezone TIMEZONE] [--lang LANG] [--online] [--offline] [--wlan-ssid WLAN_SSID] [--wlan-password WLAN_PASSWORD] [--color {White,Red,Green,Yellow,Blue,Magenta,Cyan,Light gray,Light red,Light green,Light yellow,Light blue,Light magenta,Light cyan}] name</div>
<div style="margin:0 50px"><br />
<b>name</b><br /><div style="margin:0 50px">Host's name, used to refer to the host when performing other actions. (Required)</div><br />
</div>
Options:
<div style="margin:0 50px">
<b>--boot-device</b><br /><div style="margin:0 50px">Path to virtual device for the SD card or USB key.</div><br />
<b>--zero-device</b><br /><div style="margin:0 50px">Zero the target device before copying the installation image to it. (Default: False)</div><br />
<b>--no-confirm</b><br /><div style="margin:0 50px">Don't ask for confirmation. (Default: False)</div><br />
<b>--image</b><br /><div style="margin:0 50px">Path to installation image</div><br />
<b>--ifname</b><br /><div style="margin:0 50px">Network interface (Default: `eth0` for online host, `eth1` for offline host) </div><br />
<b>--no-wait</b><br /><div style="margin:0 50px">Do not wait for the host to be ready (Default: False)</div><br />
<b>--timeout</b><br /><div style="margin:0 50px">Maximum wait time for the host to be ready, in seconds. Specify `0` for no limit. (Default: 600)</div><br />
<b>--force</b><br /><div style="margin:0 50px">Overwrite the configuration for an existing host (Default: False)</div><br />
<b>--public-key-path</b><br /><div style="margin:0 50px">Path to public key used to access the host (Default: automatically generated and stored on the boot device and locally in `~/.local/tower/hosts/`)</div><br />
<b>--private-key-path</b><br /><div style="margin:0 50px">Path to private key used to access the host (Default: automatically generated and stored locally in `~/.local/tower/hosts/`)</div><br />
<b>--password</b><br /><div style="margin:0 50px">Password to access the host (Default: automatically generated and stored locally in `~/.local/tower/hosts/`)</div><br />
<b>--keyboard-layout</b><br /><div style="margin:0 50px">Keyboard layout code (Default: same as that of the thin client)</div><br />
<b>--keyboard-variant</b><br /><div style="margin:0 50px">Keyboard variant code (Default: same as that of the thin client)</div><br />
<b>--timezone</b><br /><div style="margin:0 50px">Timezone of the host. e.g. `Europe/Paris` (Default: same as that of the thin client)</div><br />
<b>--lang</b><br /><div style="margin:0 50px">Language of the host. e.g. `en_US` (Default: same as that of the thin client)</div><br />
<b>--online</b><br /><div style="margin:0 50px">Host *WILL* be able to access the Internet via the router. (Default: False)</div><br />
<b>--offline</b><br /><div style="margin:0 50px">Host will *NOT* be able to access the Internet via the router. (Default: False)</div><br />
<b>--wlan-ssid</b><br /><div style="margin:0 50px">WiFi SSID (Default: same as that currently in use by the thin client)</div><br />
<b>--wlan-password</b><br /><div style="margin:0 50px">WiFi password (Default: same as that currently currently in use by the thin client)</div><br />
<b>--color</b><br /><div style="margin:0 50px">Color used for shell prompt and GUI. (Default: sequentially from the list, next: Yellow)</div><br />
</div>
### `tower upgrade`
<div style="margin:0 50px; font-family:Courier">usage: tower upgrade [-h] [--hosts [HOSTS ...]] [--install-device [INSTALL_DEVICE ...]] [--boot-device BOOT_DEVICE] [--zero-device] [--no-confirm] [--image IMAGE] [--ifname IFNAME] [--no-wait] [--timeout TIMEOUT] [--force]</div>
Options:
<div style="margin:0 50px">
<b>--hosts</b><br /><div style="margin:0 50px">Hosts names to upgrade. (Default: all)</div><br />
<b>--install-device</b><br /><div style="margin:0 50px">Path to virtual device for the SD card or USB key.</div><br />
<b>--boot-device</b><br /><div style="margin:0 50px">Path to virtual device for the SD card or USB key.</div><br />
<b>--zero-device</b><br /><div style="margin:0 50px">Zero the target device before copying the installation image to it. (Default: False)</div><br />
<b>--no-confirm</b><br /><div style="margin:0 50px">Don't ask for confirmation. (Default: False)</div><br />
<b>--image</b><br /><div style="margin:0 50px">Path to installation image</div><br />
<b>--ifname</b><br /><div style="margin:0 50px">Network interface (Default: `eth0` for online host, `eth1` for offline host) </div><br />
<b>--no-wait</b><br /><div style="margin:0 50px">Do not wait for the host to be ready (Default: False)</div><br />
<b>--timeout</b><br /><div style="margin:0 50px">Maximum wait time for the host to be ready, in seconds. Specify `0` for no limit. (Default: 600)</div><br />
<b>--force</b><br /><div style="margin:0 50px">Overwrite the configuration for an existing host (Default: False)</div><br />
</div>
### `tower install`
<div style="margin:0 50px; font-family:Courier">usage: tower install [-h] host packages [packages ...]</div>
<div style="margin:0 50px"><br />
<b>host</b><br /><div style="margin:0 50px">Host to install the package on (Required)</div><br />
<b>packages</b><br /><div style="margin:0 50px">Package(s) to install (Required).</div><br />
</div>
### `tower run`
<div style="margin:0 50px; font-family:Courier">usage: tower run [-h] [--uncolored] [--vnc-speeds VNC_SPEEDS] [--vnc-grab] host run_command [run_command ...]</div>
<div style="margin:0 50px"><br />
<b>host</b><br /><div style="margin:0 50px">Host's name. This name must match the `name` used with the `provision` command. (Required)</div><br />
<b>run_command</b><br /><div style="margin:0 50px">Command to execute on the host with NX protocol. (Required)</div><br />
</div>
Options:
<div style="margin:0 50px">
<b>--uncolored</b><br /><div style="margin:0 50px">Don't use host color for window headerbar. (Default: False)</div><br />
<b>--vnc-speeds</b><br /><div style="margin:0 50px">The triple rd,bw,lat corresponds to video h/w read rate in MB/sec, network bandwidth to clients in KB/sec, and network latency to clients in milliseconds, respectively. If a value is left blank, e.g. "-speeds ,100,15", then the internal scheme is used to estimate the empty value(s).</div><br />
<b>--vnc-grab</b><br /><div style="margin:0 50px">Grab host keyboard and mouse events (run x11vnc with -grabkbd and -grabptr flags). (Default: False except for Firefox)</div><br />
</div>
### `tower status`
<div style="margin:0 50px; font-family:Courier">usage: tower status [-h] [--host HOST] [--json]</div>
Options:
<div style="margin:0 50px">
<b>--host</b><br /><div style="margin:0 50px">Name of the host you want to check the status. If not specified, the status of all hosts will be displayed.</div><br />
<b>--json</b><br /><div style="margin:0 50px">Json output. (Default: False)</div><br />
</div>
### `tower wlan-connect`
<div style="margin:0 50px; font-family:Courier">usage: tower wlan-connect [-h] --ssid SSID --password PASSWORD</div>
Options:
<div style="margin:0 50px">
<b>--ssid</b><br /><div style="margin:0 50px">WiFi SSID</div><br />
<b>--password</b><br /><div style="margin:0 50px">WiFi password</div><br />
</div>
### `tower version`
<div style="margin:0 50px; font-family:Courier">usage: tower version [-h]</div>
### `tower poweroff`
<div style="margin:0 50px; font-family:Courier">usage: tower poweroff [-h] [--host HOST]</div>
Options:
<div style="margin:0 50px">
<b>--host</b><br /><div style="margin:0 50px">Name of the host you want to poweroff.</div><br />
</div>
### `tower deprovision`
<div style="margin:0 50px; font-family:Courier">usage: tower deprovision [-h] [--no-confirm] name</div>
<div style="margin:0 50px"><br />
<b>name</b><br /><div style="margin:0 50px">Host's name to delete (Required)</div><br />
</div>
Options:
<div style="margin:0 50px">
<b>--no-confirm</b><br /><div style="margin:0 50px">Don't ask for confirmation. (Default: False)</div><br />
</div>
## OPTIONS
<div style="margin:0 50px">
<b>--quiet</b><br /><div style="margin:0 50px">Set log level to ERROR.</div><br />
<b>--verbose</b><br /><div style="margin:0 50px">Set log level to DEBUG.</div><br />
</div>
