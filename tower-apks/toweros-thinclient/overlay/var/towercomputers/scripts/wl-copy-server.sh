#!/bin/bash

while (true); do
    WAYLAND_OWNER=$(ps -axu | grep 'labwc' | grep -v 'grep' | awk '{print $1}')
    if [ "$WAYLAND_OWNER" != "" ]; then
        XDG_RUNTIME_DIR="/tmp/$(id -u $WAYLAND_OWNER)-runtime-dir"
        COPY_CMD="WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR nc -l -s 127.0.0.1 -p 5556 -e wl-copy"
        while (true); do
            runuser -u "$WAYLAND_OWNER" -- bash -c "$COPY_CMD";
        done
    fi
done
