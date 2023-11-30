#!/usr/bin/env python3

import json
import os

from sh import tower

from towerlib import config

with open(os.path.join(config.TOWER_DIR, 'status'), 'w') as fp:
    all_status = json.loads(tower('status').strip())
    for host_status in all_status:
        host = host_status['name']
        status = "green" if host_status['status'] == "up" else "red"
        fp.write(f"{host}={status}\n")
        