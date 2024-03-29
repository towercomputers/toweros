#!/bin/bash
# based on https://wiki.archlinux.org/title/Simple_stateful_firewall

set -e
set -x

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

# reject all forward traffic
iptables -A FORWARD -j logdrop
# allow all outbound traffic
iptables -A OUTPUT -j logaccept

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
# drop all other traffic
iptables -A INPUT -j logdrop

# save rules
/etc/init.d/iptables save
