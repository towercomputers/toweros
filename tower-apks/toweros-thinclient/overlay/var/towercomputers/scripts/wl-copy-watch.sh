#!/bin/bash

SCRIPTS_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

while (true); do
    WAYLAND_OWNER=$(ps -axu | grep 'labwc' | grep -v 'grep' | awk '{print $1}')
    if [ "$WAYLAND_OWNER" != "" ]; then
        XDG_RUNTIME_DIR="/tmp/$(id -u $WAYLAND_OWNER)-runtime-dir"
        OLD_CONTENT_FILE="/tmp/tower-copy-watch"
        rm -f $OLD_CONTENT_FILE
        # watch clipboard for changes
        WATCH_CMD="WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR wl-paste --watch sh $SCRIPTS_DIR/wl-copy-publish.sh"
        runuser -u "$WAYLAND_OWNER" -- bash -c "$WATCH_CMD"
    fi
    sleep 1
done
