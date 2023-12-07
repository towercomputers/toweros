#!/usr/bin/env python3

import os

from towerlib import config
from towerlib import sshconf

with open(os.path.join(config.TOWER_DIR, 'status'), 'w', encoding="UTF-8") as fp:
    for host_status in sshconf.status():
        host = host_status['name']
        STATUS = "green" if host_status['status'] == "up" else "red"
        fp.write(f"{host}={STATUS}\n")
