#!/bin/bash

SCRIPTS_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

OLD_CONTENT_FILE="/tmp/tower-copy-watch"
rm -f $OLD_CONTENT_FILE

# watch clipboard for changes
WAYLAND_DISPLAY=wayland-0 wl-paste --watch sh $SCRIPTS_DIR/wl-copy-publish.sh
