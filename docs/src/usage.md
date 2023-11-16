# Usage

Hosts are divided into two types: *online* and *offline*. Online hosts live on a separate LAN from offline hosts, and the thin client is connected to both networks. One online host is deemed the “router”, and the router is responsible for providing Internet access to the thin client and all other hosts. If you do not wish to maintain two separate networks, you can simply not provision any offline hosts.

## Provisioning Hosts
TowerOS provides tools for easily provisioning new hosts with the following steps, with the user guided through them by the `tower` CLI tool:

1. Insert the root device (SD card or USB key for RPI, M.2 SSD for CM4) into the **host hardware**.
2. Insert the boot device (SD card or USB key for RPI, SD card for CM4) into the **thin client**.
3. Call the `[thinclient]$ tower provision` command to prepare the boot device.
4. Remove the boot device from the thin client and insert it into the target host hardware.
5. Turn on the host hardware.
6. Wait for the provisioning process to complete on the thin client.

*NOTE:* You must provision a router before you provision any other online hosts.

### Provision the Router
The first online host that you must provision is the router, which connect to the Internet _via_ a WiFi network: 

```
[thinclient]$ tower provision router –wlan-ssid <ssid> –wlan-password <password>
```

### Provision an Online Host
Once the `router` is correctly provisioned, you may provision other online hosts:

```
[thinclient]$ tower provision <host> --online
```

### Provision an Offline Host
An offline host is a host without access to the Internet _via_ the router.

```
[thinclient]$ tower provision <host> --offline
```

## Using TowerOS
Once your hosts are provisioned, you are ready to use TowerOS. You can of course access each host _via_ SSH. However, you can also run GUI applications installed on a host such that the application appears to run on the thin client.

### Execute a command on one of the hosts

Run a command on a host with SSH:

```
[thinclient]$ ssh <host> <command>
```

### Run a graphical application on a host, with its GUI appearing on the thin client

```
[thinclient]$ tower run <host> <command>
```

### Install an Alpine package on a host
TowerOS makes it easy to install new packages on any host by tunneling a connection through the router:

```
[thinclient]$ tower install <host> <package>
```

### List your hosts and their statuses

```
[thinclient]$ tower status
```

### Move a file from one host to another

```
[thinclient]$ scp <host_source>:<file_path_in_host_source> <host_dest>:<file_path_in_host_dest>
[thinclient]$ ssh <host_source> rm <file_path_in_host_source>
```

## Example Usage

1. Provision the router:

        [thinclient]$ tower provision router –wlan-ssid <ssid> –wlan-password <password>

1. Provision an offline host named `office`:

        [thinclient]$ tower provision office

1. Install GCalculator on the `office` offline host:

        [thinclient]$ tower install office galculator

1. Run galculator `office`:

        [thinclient]$ startx
        [thinclient]$ tower run office gcalculator

1. Move a file from `router` to `office`:

        [thinclient]$ scp router:/home/tower/myfile office:/home/tower
        [thinclient]$ ssh router rm /home/tower/myfile

## Backup hosts with `restic`

It is recommended to reserve one of your hosts, for example `storage`, to store the backups of all the other hosts there. Here's how, using `restic`, you can store the backup of an `office` host on a `storage` host:

1. Install restic

        [thinclient]$ tower install storage restic
        [thinclient]$ tower install office restic
        [thinclient]$ tower install thinclient restic

1. Initialize restic repo in each host
        
        [thinclient]$ ssh -t storage restic -r /home/tower/backup init
        [thinclient]$ ssh -t office restic -r /home/tower/backup init \
                                           --from-repo sftp:storage:/home/tower/backup \
                                           --copy-chunker-params

    Note: `--copy-chunker-params` is important to ensure deduplication. 
    See "[Copying snapshots between repositories](https://restic.readthedocs.io/en/latest/045_working_with_repos.html#copying-snapshots-between-repositories)" for more options.

1. Backup `office`

        [thinclient]$ ssh -t office restic -r /home/tower/backup backup /home/tower/mydata

1. Copy `office` snapshot into `storage` repo

        [thinclient]$ restic -r sftp:storage:/home/tower/backup copy \
                             --from-repo sftp:office:/home/tower/backup \
                             latest

    Note: here `restic` copies the backup from the `office` host to the Thin Client, and then copies it to the `storage` host. You can optionally clear the cache stored on the Thin Client:
        
        [thinclient]$ rm -rf ~/.cache/restic

1. Restore backup into `office`

        [thinclient]$ restic -r sftp:office:/home/tower/backup copy \
                             --from-repo sftp:storage:/home/tower/backup \
                             latest --host office
        [thinclient]$ ssh -t office restic -r /home/tower/backup restore latest --target /