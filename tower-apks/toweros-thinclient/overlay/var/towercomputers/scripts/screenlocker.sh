#!/bin/bash

if [ $(ps -ax | grep 'physlock' | grep -vc 'grep') -gt 0 ]; then
    echo "physlock already running"
    exit 0
fi
if [ $(ps -ax | grep 'labwc' | grep -vc 'grep') -gt 0 ]; then
    echo "Labwc already running"
    exit 0
fi

if [ -f /home/$USER/.local/tower/osconfig ]; then
    source /home/$USER/.local/tower/osconfig
fi
LOCK_SCREEN_AFTER=${LOCK_SCREEN_AFTER:-"300"}

LAST_MODIFIED_TTY=$(ls -lt /dev/tty? | head -1 | awk '{print $NF}')
INACTIVITY_DURATION=$(($(date +%s) - $(date -r $LAST_MODIFIED_TTY +%s)))

if [ $INACTIVITY_DURATION -gt $LOCK_SCREEN_AFTER ]; then
    physlock &
fi
