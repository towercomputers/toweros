#!/bin/bash

# find all running Xvfb processes and copy the content of the clipboard
for d in $(ps -ax | grep "\-\- /usr/bin/Xvfb :" | awk '{print $9}'); do
    DISPLAY=$d xclip -sel c
done
