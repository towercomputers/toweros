## 1. Provision a host

Prepare the sd-card in the Thin Client with the command bellow. Once the sd-card is ready you must insert it into the Raspberry Pi or CM4 and turn it on.

```
$> tower provision <host> --offline
```

or, for an online host:

```
$> tower provision <host> --online
```

Keyboard, timezone and WiFi parameters are retrieved from the Thin Client. You can customize them with the appropriate argument (see `tower provision --help`).

## 2. Execute a command on one of the hosts

Run a command on a host with SSH:

```
$> ssh <host> ls ~/
```

or a graphical application with NX protocol:

```
$> tower run <host> <application-name>
```

## 3. Install an application on one of the hosts

```
$> tower install <host> <application-name>
```

or, if the host is offline, you can tunnel the installation through an online host:

```
$> tower install <offline-host> <application-name> --online-host <online-host> 
```

## 4. List hosts and their statuses

```
$> tower status
```

## 5. Example using two hosts

Provision the first offline host named `office`.

```
$> tower provision office
```

Provision a second online host named `web`.

```
$> tower provision web --online –wlan-ssid <ssid> –wlan-password <password>
```

Install galculator on the `office` offline host.

```
$> tower install office galculator --online-host=web
```

Run galculator from `office`.

```
$> startx
$> tower run office gcalculator
```