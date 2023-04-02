#!/bin/bash

set +e
set -x

THIN_CLIENT_IP=$1
TOWER_NETWORK=$2

# based on https://wiki.archlinux.org/title/Simple_stateful_firewall

# create user defined chains
iptables -N TCP
iptables -N UDP
# reject all forward traffic
iptables -P FORWARD DROP
# allow all outbound traffic
iptables -P OUTPUT ACCEPT
# drop all input traffic by default
iptables -P INPUT DROP
# allow ICMP messages
iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
# allow local traffic
iptables -A INPUT -i lo -j ACCEPT
# drop all traffic with an "INVALID" state 
iptables -A INPUT -m conntrack --ctstate INVALID -j DROP
# allow ICMP echo requests (pings)
iptables -A INPUT -p icmp --icmp-type 8 -m conntrack --ctstate NEW -j ACCEPT
# attach the TCP and UDP chains to the INPUT
iptables -A INPUT -p udp -m conntrack --ctstate NEW -j UDP
iptables -A INPUT -p tcp --syn -m conntrack --ctstate NEW -j TCP
# reject UDP streams with ICMP port unreachable messages
iptables -A INPUT -p udp -j REJECT --reject-with icmp-port-unreachable
# reject TCP connections with TCP RESET 
iptables -A INPUT -p tcp -j REJECT --reject-with tcp-reset
# protection against spoofing attacks
iptables -t mangle -I PREROUTING -m rpfilter --invert -j DROP
# block SYN port scanning
iptables -I TCP -p tcp -m recent --update --rsource --seconds 60 --name TCP-PORTSCAN -j REJECT --reject-with tcp-reset
iptables -D INPUT -p tcp -j REJECT --reject-with tcp-reset
iptables -A INPUT -p tcp -m recent --set --rsource --name TCP-PORTSCAN -j REJECT --reject-with tcp-reset
# block UDP port scanning
iptables -I UDP -p udp -m recent --update --rsource --seconds 60 --name UDP-PORTSCAN -j REJECT --reject-with icmp-port-unreachable
iptables -D INPUT -p udp -j REJECT --reject-with icmp-port-unreachable
iptables -A INPUT -p udp -m recent --set --rsource --name UDP-PORTSCAN -j REJECT --reject-with icmp-port-unreachable
# reject all remaining incoming traffic with icmp protocol unreachable messages
iptables -A INPUT -j REJECT --reject-with icmp-proto-unreachable
# open port for avahi
iptables -I UDP -i eth0 -s $THIN_CLIENT_IP -p udp -m udp --dport 5353 -j ACCEPT
# open port for ssh connection from thin client
iptables -A TCP -p tcp -s $THIN_CLIENT_IP --dport 22 -j ACCEPT
# reject traffic from host to thin client and other hosts
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -d $TOWER_NETWORK -j DROP

# save rules
iptables-save -f /etc/iptables/iptables.rules