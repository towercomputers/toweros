#!/bin/bash

LAST_CONTENT=$(DISPLAY=$1 xclip -o -sel cl)

while $(DISPLAY=$1 clipnotify -s clipboard); do
    CONTENT=$(DISPLAY=$1 xclip -o -sel cl)
    if [ "$CONTENT" != "$LAST_CONTENT" ]; then
         echo -n $CONTENT | nc 127.0.0.1 5557
        LAST_CONTENT=$CONTENT
    fi
done