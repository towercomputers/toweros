#!/bin/bash

NEW_CONTENT="$(cat)"

if [ "$NEW_CONTENT" == "" ]; then
    exit 0
fi

OLD_CONTENT_FILE="/tmp/tower-copy-watch"
if [ -f $OLD_CONTENT_FILE ]; then
    OLD_CONTENT=$(cat $OLD_CONTENT_FILE)
else
    OLD_CONTENT=""
fi

if [ "$NEW_CONTENT" != "$OLD_CONTENT" ]; then
    echo -n $NEW_CONTENT > $OLD_CONTENT_FILE
    for port in $(ps -ax | grep '\-R 5557:localhost:5556 -L ' |  grep -v 'grep' | grep -v 'runuser' | awk '{print $10}' | awk -F  ':' '{print $1}'); do
        echo -n "$NEW_CONTENT" | nc -w 1 localhost $port
    done
fi
