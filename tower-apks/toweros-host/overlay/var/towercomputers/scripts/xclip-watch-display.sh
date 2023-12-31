#!/bin/bash

DISPLAY_OWNER=$(ps -axu | grep "\-\- /usr/bin/Xvfb $1" | awk '{print $1}')

LAST_CONTENT=$(DISPLAY="$1" runuser -u "$DISPLAY_OWNER" -- xclip -o -sel cl)

while $(DISPLAY="$1" runuser -u "$DISPLAY_OWNER" -- clipnotify -s clipboard); do
    CONTENT=$(DISPLAY="$1" runuser -u "$DISPLAY_OWNER "-- xclip -o -sel cl)
    if [ "$CONTENT" != "$LAST_CONTENT" ]; then
        echo -n "$CONTENT"| nc -w 1 127.0.0.1 5557
        LAST_CONTENT="$CONTENT"
    fi
done
