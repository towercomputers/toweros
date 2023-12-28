# prompt format
export PS1='[\\u@\\H \\W]\\$ '

# initialize XDG_RUNTIME_DIR
if [ -z "$XDG_RUNTIME_DIR" ]; then
    XDG_RUNTIME_DIR="/tmp/$(id -u)-runtime-dir"
	mkdir -pm 0700 "$XDG_RUNTIME_DIR"
	export XDG_RUNTIME_DIR
fi

# load bash completion
source /etc/bash/bash_completion.sh

# useful aliases
alias startw='dbus-launch labwc'

# load toweros config
if [ -f ~/.local/tower/osconfig ]; then
    source ~/.local/tower/osconfig
fi

# start actkbd.py and supercronic
if [ "$(tty)" == "/dev/tty1" ]; then
    /var/towercomputers/scripts/actkbd.py >/dev/null 2>&1 &
    supercronic /etc/crontabs/supercronic >/dev/null 2>&1 &
fi

# start labwc on login
STARTW_ON_LOGIN=${STARTW_ON_LOGIN:-"false"}
if [ -z "$DISPLAY" ] && [ "$(tty)" == "/dev/tty1" ] && [ "$STARTW_ON_LOGIN" == "true" ]; then
    dbus-launch labwc; 
fi

# ensure that tower.widget is linked
ln -s ~/.local/tower/tower.widget /usr/local/share/sfwbar/tower.widget || true