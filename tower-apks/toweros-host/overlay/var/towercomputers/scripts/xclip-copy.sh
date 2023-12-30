#!/bin/bash

NEW_CONTENT="$(cat)"

# find all running Xvfb processes and copy the content of the clipboard
for d in $(ps -ax | grep "\-\- /usr/bin/Xvfb :" | awk '{print $9}'); do
    DISPLAY_OWNER=$(ps -axu | grep "\-\- /usr/bin/Xvfb $d" | awk '{print $1}')
    echo -n "$NEW_CONTENT" > /tmp/tower-copy-watch-$d
    runuser -u $DISPLAY_OWNER -- xclip -sel c -d $d /tmp/tower-copy-watch-$d
done
