#!/bin/bash

while (true); do
    nc -l -s 127.0.0.1 -p 5556 -e sh /var/towercomputers/scripts/xclip-copy
done