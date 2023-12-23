#!/usr/bin/env python3

import evdev
# pylint: disable=no-name-in-module
from sh import pactl, Command

DEFAULT_DEVICE = "/dev/input/event0"

def get_current_volume():
    volume = Command("sh")('-c', "pactl get-sink-volume @DEFAULT_SINK@ | head -1 | awk '{print $5}'")
    return int(volume.strip("%\n"))

def mute_volume():
    pactl("set-sink-mute", "@DEFAULT_SINK@", "toggle")
    pactl("get-sink-mute", "@DEFAULT_SINK@", _out=print)

def increase_volume(delta = 5):
    current_volume = get_current_volume()
    if current_volume + delta > 100:
        delta = 100 - current_volume
    if delta > 0:
        pactl("set-sink-volume", "@DEFAULT_SINK@", f"+{delta}%")
        print(f"New volume: {get_current_volume()}%")

def decrease_volume(delta = 5):
    current_volume = get_current_volume()
    if current_volume - delta < 0:
        delta = current_volume
    if delta > 0:
        pactl("set-sink-volume", "@DEFAULT_SINK@", f"-{delta}%")
        print(f"New volume: {get_current_volume()}%")

EVENTS = {
    '113_DOWN': mute_volume,
    '113_HOLD': mute_volume,
    '114_DOWN': decrease_volume,
    '114_HOLD': decrease_volume,
    '115_DOWN': increase_volume,
    '115_HOLD': increase_volume,
}

KEY_STATE = ["UP", "DOWN", "HOLD"]

for event in evdev.InputDevice(DEFAULT_DEVICE).read_loop():
    if event.type == evdev.ecodes.EV_KEY:
        categorized_event = evdev.categorize(event)
        event_name = f"{categorized_event.scancode}_{KEY_STATE[categorized_event.keystate]}"
        if event_name in EVENTS:
            EVENTS[event_name]()
