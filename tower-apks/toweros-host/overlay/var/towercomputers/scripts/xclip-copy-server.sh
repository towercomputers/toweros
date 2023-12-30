#!/bin/bash

SCRIPTS_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"

while (true); do
    nc -l -s 127.0.0.1 -p 5556 -e sh $SCRIPTS_DIR/xclip-copy.sh
done
