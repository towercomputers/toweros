#!/usr/bin/env python3

import json
import os

from sh import tower

from towerlib import config

with open(os.path.join(config.TOWER_DIR, 'status'), 'w', encoding="UTF-8") as fp:
    all_status = json.loads(tower('status').strip())
    for host_status in all_status:
        host = host_status['name']
        STATUS = "green" if host_status['status'] == "up" else "red"
        fp.write(f"{host}={STATUS}\n")
