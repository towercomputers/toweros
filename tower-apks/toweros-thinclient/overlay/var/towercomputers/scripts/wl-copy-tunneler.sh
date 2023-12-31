#!/bin/bash

while (true); do
    WAYLAND_OWNER=$(ps -axu | grep 'labwc' | grep -v 'grep' | awk '{print $1}')
    if [ "$WAYLAND_OWNER" != "" ]; then
        # find all running x11vnc processes and open a tunnel for each host
        for host in $(ps -ax | grep 'x11vnc -create' | grep -v 'grep' | awk '{print $6}'); do
            if [ $(ps -ax | grep "ssh $host -R 5557:localhost:5556 -L 5557:localhost:5556" |  grep -vc 'grep') -eq 0 ]; then
                runuser -u $WAYLAND_OWNER -- ssh $host -R 5557:localhost:5556 -L 5557:localhost:5556 -N &
            fi
        done
        # find all running tunnels and kill them if their x11vnc process is not running
        for host in $(ps -ax | grep '\-R 5557:localhost:5556 -L 5557:localhost:5556' |  grep -v 'grep' | grep -v 'runuser' | awk '{print $6}'); do
            if [ $(ps -ax | grep -E "ssh $host.*x11vnc -create" | grep -vc 'grep') -eq 0 ]; then
                kill $(ps -ax | grep "ssh $host -R 5557:localhost:5556 -L 5557:localhost:5556" | grep -v 'grep' | awk '{print $1}') > /dev/null 2>&1
            fi
        done
    fi
    sleep 1
done