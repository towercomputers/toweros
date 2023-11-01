## 1. Provision an online host

Only one of the hosts is connected to the internet via WIFI. This host, called the `router`, is then responsible for sharing the connection with all the other online hosts. The first online host that you can/must provision is therefore the router:

```
$> tower provision router –wlan-ssid <ssid> –wlan-password <password>
```

Once the `router` is correctly provisioned, you can provision other online hosts:

```
$> tower provision <host> --online
```

Keyboard, timezone and WiFi parameters are retrieved from the Thin Client. You can customize them with the appropriate argument (see `tower provision --help`).

## 2. Provision an offline host

Prepare the sd-card in the Thin Client with the command bellow. Once the sd-card is ready you must insert it into the Raspberry Pi or CM4 and turn it on.

```
$> tower provision <host> --offline
```

## 3. Execute a command on one of the hosts

Run a command on a host with SSH:

```
$> ssh <host> ls ~/
```

or a graphical application with NX protocol:

```
$> tower run <host> <application-name>
```

## 4. Install an application on one of the hosts

```
$> tower install <host> <application-name>
```

Important: To be able to install packages on offline hosts you must first provision the `router`.

## 5. List hosts and their statuses

```
$> tower status
```

## 6. Example using two hosts

Provision the router.

```
$> tower provision router –wlan-ssid <ssid> –wlan-password <password>
```

Provision an offline host named `office`.

```
$> tower provision office
```

Install galculator on the `office` offline host.

```
$> tower install office galculator
```

Run galculator from `office`.

```
$> startx
$> tower run office gcalculator
```