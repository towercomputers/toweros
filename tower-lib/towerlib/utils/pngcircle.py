#!/usr/bin/env python3

import os

from PIL import Image, ImageDraw

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALLER_DIR = os.path.join(CURRENT_DIR, '..', '..', 'toweros-installers', 'toweros-thinclient', 'installer')
ICON_DIR = os.path.join(INSTALLER_DIR, 'icons')

#from towerlib.sshconf import COLORS
COLORS = [
    [39, "White", "ffffff"],
    [31, "Red", "cc0000"],
    [32, "Green", "4e9a06"],
    [33, "Yellow", "c4a000"],
    [34, "Blue", "729fcf"],
    [35, "Magenta", "75507b"],
    [36, "Cyan", "06989a"],
    [37, "Light gray", "d3d7cf"],
    [91, "Light red", "ef2929"],
    [92, "Light green", "8ae234"],
    [93, "Light yellow", "fce94f"],
    [94, "Light blue", "32afff"],
    [95, "Light magenta", "ad7fa8"],
    [96, "Light cyan", "34e2e2"],
]

def generate_circle_image(color):
    image = Image.new('RGBA', (48, 48))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 40, 40), fill=f"#{color[2]}", outline='black')
    image.save(f"{ICON_DIR}/circle-{color[1].replace(' ', '-').lower()}.png")

def generate_circle_images():
    for color in COLORS:
        generate_circle_image(color)

if __name__ == '__main__':
    generate_circle_images()