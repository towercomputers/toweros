# Development Guide

## 1. Setup environement

Connect to internet with:

```
$> setup-wifi <ssid> <password>
```

Configure `git`, download Github repository in `~/towercomputers/tools` and install `hatch` with:

```
$> ~/install-dev.sh <git-name> <git-email> <git-private-key-path>
```

## 2. Test with hatch

```
$> cd ~/towercomputers/tools
$> hatch run tower --help
$> hatch run build-tower-image --help
```

## 3. Manually QA TowerOS-ThinClient release

On first boot:

1. Basic checking

- Welcome message should be customized.
- README, whitepaper and install-dev.sh should be in ~/.
- wheel package and host image should be in ~/.cache/tower/builds.
- iptables -L -v should show firewall rules and /var/logs/iptables.log should contain firewall logs.
- `lo` and `eth0` should be up (check  with `ip ad`)

2. Provision an online host:

```
$> tower provision web --online --wlan-ssid <ssid> --wlan-password <password> --sd-card /dev/sdb 
```

3. Provision an offline host:

```
$> tower provision office --offline --sd-card /dev/sdb
```

4. Check status:

```
$> tower status
```

5. Install package in offline host:

```
$> tower install office xcalc --online-host office
```

6. Install package in online host:

```
$> tower install web midori
```

7. Test installed packages

```
$> startx
$> tower run office xcalc
$> tower run web midori
```

Check also if the Application menu contains shortcuts for installed packages.

8. Logout from `xfce` and connect to internet:

```
$> setup-wifi <ssid> <password>
```

9. Build an host image with:

```
$> buld-tower-image host
```

10. Build a thinclient image with:

```
$> buld-tower-image thinclient
```

11. Install development environment with:

```
$> ~/install-dev.sh <git-name> <git-email> <git-private-key-path>
```

12. If you are brave redo all these tests with the image generated in step 10 :)
