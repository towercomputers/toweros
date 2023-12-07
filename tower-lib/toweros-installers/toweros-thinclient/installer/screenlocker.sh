#!/bin/bash

LOCK_AFTER=300 # 5 minutes
LAST_MODIFIED_TTY=$(ls -lt /dev/tty* | head -1 | awk '{print $NF}')
INACTIVITY_DURATION=$(($(date +%s) - $(date -r $LAST_MODIFIED_TTY +%s)))

if [ $INACTIVITY_DURATION -gt 60 ]; then
    if ps -a | grep physlock; then
        echo "physlock already running"
    else
        physlock &
    fi
fi
