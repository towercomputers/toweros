#!/usr/bin/env python3

import subprocess # nosec B404
import json
import sys

def run_cmd(cmd, to_json=False):
    out = subprocess.run(cmd, capture_output=True, encoding="UTF-8", check=False).stdout.strip() # nosec B603
    if to_json:
        return json.loads(out)
    return out

def search_windows(name):
    return run_cmd(["xdotool", "search", "--onlyvisible", "--name", name]).split("\n")

def resize_window(name, width, height):
    window_ids = search_windows(name)
    for window_id in window_ids:
        win_type = run_cmd(["xprop", "-id", window_id, "_NET_WM_WINDOW_TYPE"]).split("=")[-1].strip()
        if win_type == "_NET_WM_WINDOW_TYPE_NORMAL":
            run_cmd(["xdotool", "windowsize", '--sync', window_id, width, height])

if __name__ == '__main__':
    window_name = sys.argv[1]
    window_width = sys.argv[2]
    window_height = sys.argv[3]
    sys.exit(resize_window(window_name, window_width, window_height))
