# prompt format
export PS1='[\u@\H \W]\$ '

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
    # ensure actkbd.py is running
    if [ $(ps -ax | grep 'actkbd' | grep -vc 'grep') -eq 0 ]; then
        python /var/towercomputers/scripts/actkbd.py >/dev/null 2>&1 &
    fi
    # ensure supercronic is running
    if [ $(ps -ax | grep 'supercronic' | grep -vc 'grep') -eq 0 ]; then
        supercronic /etc/crontabs/supercronic >/dev/null 2>&1 &
    fi
    # ensure that tower.widget is linked
    if [ ! -L /usr/share/sfwbar/tower.widget ]; then
        doas ln -s ~/.local/tower/tower.widget /usr/share/sfwbar/tower.widget
    fi
    # ensure sudo is an alias to doas
    if [ ! -L /usr/bin/sudo ]; then
        doas ln -s /usr/bin/doas /usr/bin/sudo
    fi
    # start labwc on login
    STARTW_ON_LOGIN=${STARTW_ON_LOGIN:-"false"}
    if [ -z "$DISPLAY" ] && [ "$STARTW_ON_LOGIN" == "true" ]; then
        dbus-launch labwc;
    fi
fi
