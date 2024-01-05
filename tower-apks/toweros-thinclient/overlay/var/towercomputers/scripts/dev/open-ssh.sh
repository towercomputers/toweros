set -e
set -x

AUTHORIZED_KEY="$1"

# start sshd and open firewall access
if [ ! -z "$AUTHORIZED_KEY" ]; then
    sudo iptables -A TCP -p tcp --dport 22 -j ACCEPT
    sudo iptables -D INPUT -j logreject-icmpproto
    sudo iptables -A INPUT -j logreject-icmpproto
    sudo /etc/init.d/iptables save
    sudo rc-update add sshd default
    sudo rc-service sshd start
    mkdir -p ~/.ssh
    touch ~/.ssh/authorized_keys
    echo "$AUTHORIZED_KEY" > ~/.ssh/authorized_keys
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/*
else
    echo "Usage: $0 <authorized_key>"
fi
