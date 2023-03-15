#!/bin/bash

set -e

DISPLAY_NUM="$1"
NXAGENT_PORT="$2"

HOSTNAME=$(hostname)
MAGIC_COOKIE="$(mcookie)"
# let use for now this cookie as unique identifier
SESSION_ID="$MAGIC_COOKIE"

SESSION_DIR="$HOME/.nxsessions"
mkdir "$SESSION_DIR" || true

XAUTHORITYH_PATH="$HOME/.Xauthority"
rm -f $XAUTHORITYH_PATH
touch $XAUTHORITYH_PATH

# add the magic cookie in .Xauthority file
xauth -f $XAUTHORITYH_PATH add "$HOSTNAME/unix:$DISPLAY_NUM" 'MIT-MAGIC-COOKIE-1' $MAGIC_COOKIE

# start the nx agent
DISPLAY="nx/nx,accept=127.0.0.1,listen=$NXAGENT_PORT:$DISPLAY_NUM"
export DISPLAY
nxagent -R -nolisten tcp -auth $XAUTHORITYH_PATH :$DISPLAY_NUM 2> "$SESSION_DIR/$SESSION_ID.log" &
NXAGENT_PID="${!}"
echo $NXAGENT_PID > "$SESSION_DIR/$SESSION_ID.pid"

# return the magic cookie to the client, so it can use it to connect with nxproxy.
echo $MAGIC_COOKIE