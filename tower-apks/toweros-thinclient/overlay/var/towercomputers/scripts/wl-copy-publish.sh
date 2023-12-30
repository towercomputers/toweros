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
    echo -n "$NEW_CONTENT" | nc -w 1 127.0.0.1 5557
fi
