#!/bin/bash

set -e
set -x

# parameters
COMPUTER="office"
CMD="galculator"
DISPLAY_NUM="50"
NXAGENT_PORT="4001"

# copy latest startagent script to the computer
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ssh $COMPUTER rm -f /home/tower/startagent.sh
scp $SCRIPT_DIR/startagent.sh $COMPUTER:/home/tower/

# start nxagent in the COMPUTER and get the magic cookie
MAGIC_COOKIE=$(ssh $COMPUTER sh /home/tower/startagent.sh $DISPLAY_NUM $NXAGENT_PORT)

# open a SSH tunnel from nxproxy in the thin client to nxagent in the COMPUTER
ssh -NT -L $NXAGENT_PORT:127.0.0.1:$NXAGENT_PORT $COMPUTER &
SSH_TUNNEL_PID="${!}"

# start nxproxy
NX_OPTIONS='retry=5,composite=1,connect=127.0.0.1,clipboard=1'
nxproxy -S "nx/nx,$NX_OPTIONS,port=$NXAGENT_PORT,cookie=$MAGIC_COOKIE:$DISPLAY_NUM" 2> nxproxy.log &

# run the desired command in the nxagent display
ssh $COMPUTER DISPLAY=:$DISPLAY_NUM $CMD

# when closed, close the ssh tunnel
kill -9 $SSH_TUNNEL_PID
# and stop the nxagent in the COMPUTER
NXAGENT_PID=$(ssh $COMPUTER cat /home/tower/.nxsessions/$MAGIC_COOKIE.pid)
ssh $COMPUTER kill -9 $NXAGENT_PID
# nxproxy automatically stop when connection is lost with nxagent