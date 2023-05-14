
#!/bin/bash

set +e
set -x

THIN_CLIENT_IP=$1
TOWER_NETWORK=$2
ONLINE=$3

# based on https://wiki.archlinux.org/title/Simple_stateful_firewall

# log and drop packets
iptables -N logdrop
iptables -A logdrop -m limit --limit 5/m --limit-burst 10 --log-prefix "iptables: DROP: " -j LOG
iptables -A logdrop -j DROP
# log and reject packets with tcp reset
iptables -N logrejectwithtcpreset
iptables -A logrejectwithtcpreset -m limit --limit 5/m --limit-burst 10 --log-prefix "iptables: REJECT: " -j LOG
iptables -A logrejectwithtcpreset -j REJECT --reject-with tcp-reset
# log and reject packets with icmp port unreachable
iptables -N logrejectwithicmpportunreachable
iptables -A logrejectwithicmpportunreachable -m limit --limit 5/m --limit-burst 10 --log-prefix "iptables: REJECT: " -j LOG
iptables -A logrejectwithicmpportunreachable -j REJECT --reject-with icmp-port-unreachable
# log and reject packets with icmp protocol unreachable
iptables -N logrejectwithicmpprotounreachable
iptables -A logrejectwithicmpprotounreachable -m limit --limit 5/m --limit-burst 10 --log-prefix "iptables: REJECT: " -j LOG
iptables -A logrejectwithicmpprotounreachable -j REJECT --reject-with icmp-proto-unreachable
# log and accept
iptables -N logaccept
iptables -A logaccept -m limit --limit 5/m --limit-burst 10 --log-prefix "iptables: ACCEPT: " -j LOG
iptables -A logaccept -j ACCEPT

# create user defined chains
iptables -N TCP
iptables -N UDP

# reject all forward traffic
iptables -P FORWARD -j logdrop

if "$ONLINE" == "true"; then
    # allow all outbound traffic
    iptables -P OUTPUT ACCEPT
    # reject traffic from computers to thin client and other computers
    iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    iptables -A OUTPUT -d $TOWER_NETWORK -j logdrop
else
    # drop all outbound traffic except established and related connections (for ssh from thin client)
    iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    iptables -P OUTPUT -j logdrop
fi

# drop all input traffic by default
iptables -P INPUT -j logdrop
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
iptables -A INPUT -p udp -j logrejectwithicmpportunreachable
# reject TCP connections with TCP RESET 
iptables -A INPUT -p tcp -j logrejectwithtcpreset
# protection against spoofing attacks
iptables -t mangle -I PREROUTING -m rpfilter --invert -j logdrop
# block SYN port scanning
iptables -I TCP -p tcp -m recent --update --rsource --seconds 60 --name TCP-PORTSCAN -j logrejectwithtcpreset
iptables -D INPUT -p tcp -j logrejectwithtcpreset
iptables -A INPUT -p tcp -m recent --set --rsource --name TCP-PORTSCAN -j logrejectwithtcpreset
# block UDP port scanning
iptables -I UDP -p udp -m recent --update --rsource --seconds 60 --name UDP-PORTSCAN -j logrejectwithicmpportunreachable
iptables -D INPUT -p udp -j logrejectwithicmpportunreachable
iptables -A INPUT -p udp -m recent --set --rsource --name UDP-PORTSCAN -j logrejectwithicmpportunreachable
# reject all remaining incoming traffic with icmp protocol unreachable messages
iptables -A INPUT -j logrejectwithicmpprotounreachable
# open port for avahi
iptables -I UDP -i eth0 -s $THIN_CLIENT_IP -p udp -m udp --dport 5353 -j logaccept
# open port for ssh connection from thin client
iptables -A TCP -p tcp -s $THIN_CLIENT_IP --dport 22 -j logaccept

# save rules
/etc/init.d/iptables save