#!/bin/bash

SCRIPTS_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

while (true); do
    # find all running Xvfb processes and run watch script for each
    for d in $(ps -ax | grep "\-\- /usr/bin/Xvfb :" | awk '{print $9}'); do
        if [ $(ps -ax | grep "xclip-watch-display.sh $d" | grep -vc 'grep') -eq 0 ]; then
            sh $SCRIPTS_DIR/xclip-watch-display.sh $d &
        fi
    done
    # find all running watch scripts and kill them if their Xvfb process is not running
    for d in $(ps -ax | grep "xclip-watch-display.sh :" | grep -v 'grep' | awk '{print $7}'); do
        if [ $(ps -ax | grep "\-\- /usr/bin/Xvfb $d" | grep -vc 'grep') -eq 0 ]; then
            kill $(ps -ax | grep "xclip-watch-display.sh $d" | grep -v 'grep' | awk '{print $1}')
        fi
    done
    sleep 1
done