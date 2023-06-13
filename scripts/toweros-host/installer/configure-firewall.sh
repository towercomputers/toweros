
#!/bin/bash

set +e
set -x

THIN_CLIENT_IP="$1"
TOWER_NETWORK="$2"
HOSTNAME="$3"
ONLINE="$4"
ROUTER_IP="$5"

# based on https://wiki.archlinux.org/title/Simple_stateful_firewall

# clean everything
iptables -F
iptables -X
iptables -Z
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# log and drop packets
iptables -N logdrop
iptables -A logdrop -m limit --limit 5/m --limit-burst 10 -j LOG --log-prefix "iptables: DROP: "
iptables -A logdrop -j DROP
# log and drop packets
iptables -N logdropm -t mangle
iptables -A logdropm -t mangle -m limit --limit 5/m --limit-burst 10 -j LOG --log-prefix "iptables: DROP: "
iptables -A logdropm -t mangle -j DROP
# log and reject packets with tcp reset
iptables -N logreject-tcpreset
iptables -A logreject-tcpreset -m limit --limit 5/m --limit-burst 10 -j LOG --log-prefix "iptables: REJECT: "
iptables -A logreject-tcpreset -p tcp -j REJECT --reject-with tcp-reset
# log and reject packets with icmp port unreachable
iptables -N logreject-icmpport
iptables -A logreject-icmpport -m limit --limit 5/m --limit-burst 10 -j LOG --log-prefix "iptables: REJECT: "
iptables -A logreject-icmpport -p tcp -j REJECT --reject-with icmp-port-unreachable
# log and reject packets with icmp protocol unreachable
iptables -N logreject-icmpproto
iptables -A logreject-icmpproto -m limit --limit 5/m --limit-burst 10 -j LOG --log-prefix "iptables: REJECT: "
iptables -A logreject-icmpproto -p tcp -j REJECT --reject-with icmp-proto-unreachable
# log and accept
iptables -N logaccept
iptables -A logaccept -m limit --limit 5/m --limit-burst 10 -j LOG --log-prefix "iptables: ACCEPT: "
iptables -A logaccept -j ACCEPT

# create user defined chains
iptables -N TCP
iptables -N UDP

# open port for ssh connection from thin client
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j logaccept
iptables -A TCP -p tcp -s $THIN_CLIENT_IP --dport 22 -j logaccept

if [ "$HOSTNAME" == "router" ]; then
    # enable ip forwarding
    iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
    iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
else
    if [ "$ONLINE" == "true" ]; then
        # reject traffic from computers to thin client and other computers
        # except router
        iptables -A OUTPUT -s $ROUTER_IP  -j logaccept
        iptables -A OUTPUT -d $TOWER_NETWORK -j logdrop
        # allow all outbound traffic
        iptables -A OUTPUT -j logaccept
    else
        # reject all forward traffic
        iptables -A FORWARD -o lo -j logaccept
        iptables -A FORWARD -j logdrop
        # reject all output traffic
        iptables -A OUTPUT -o lo -j logaccept
        iptables -A OUTPUT -j logdrop
    fi
fi

# allow ICMP messages
iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j logaccept
# allow local traffic
iptables -A INPUT -i lo -j ACCEPT
# drop all traffic with an "INVALID" state 
iptables -A INPUT -m conntrack --ctstate INVALID -j logdrop
# allow ICMP echo requests (pings)
iptables -A INPUT -p icmp --icmp-type 8 -m conntrack --ctstate NEW -j logaccept
# attach the TCP and UDP chains to the INPUT
iptables -A INPUT -p udp -m conntrack --ctstate NEW -j UDP
iptables -A INPUT -p tcp --syn -m conntrack --ctstate NEW -j TCP
# reject UDP streams with ICMP port unreachable messages
iptables -A INPUT -p udp -j logreject-icmpport
# reject TCP connections with TCP RESET 
iptables -A INPUT -p tcp -j logreject-tcpreset
# protection against spoofing attacks
iptables -t mangle -I PREROUTING -m rpfilter --invert -j logdropm
# block SYN port scanning
iptables -I TCP -p tcp -m recent --update --rsource --seconds 60 --name TCP-PORTSCAN -j logreject-tcpreset
iptables -D INPUT -p tcp -j logreject-tcpreset
iptables -A INPUT -p tcp -m recent --set --rsource --name TCP-PORTSCAN -j logreject-tcpreset
# block UDP port scanning
iptables -I UDP -p udp -m recent --update --rsource --seconds 60 --name UDP-PORTSCAN -j logreject-icmpport
iptables -D INPUT -p udp -j logreject-icmpport
iptables -A INPUT -p udp -m recent --set --rsource --name UDP-PORTSCAN -j logreject-icmpport

# reject all remaining incoming traffic with icmp protocol unreachable messages
iptables -A INPUT -j logreject-icmpproto

# save rules
/etc/init.d/iptables save