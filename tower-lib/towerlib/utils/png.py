#!/usr/bin/env python3

import os

# pylint: disable=import-error
from PIL import Image, ImageDraw

from towerlib.config import COLORS

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALLER_DIR = os.path.join(CURRENT_DIR, '..', '..', 'toweros-installers', 'toweros-thinclient', 'installer')
ICONS_DIR = os.path.join(INSTALLER_DIR, 'icons')
BACKGROUNDS_DIR = os.path.join(INSTALLER_DIR, 'backgrounds')

def generate_circle_image(color):
    image = Image.new('RGBA', (48, 48))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 40, 40), fill=f"#{color[2]}", outline='black')
    image.save(f"{ICONS_DIR}/circle-{color[1].replace(' ', '-').lower()}.png")

def generate_circle_images():
    for color in COLORS:
        generate_circle_image(color)

def generate_header_background(color):
    image = Image.new('RGBA', (20, 20))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 20, 20), fill=f"#{color[2]}80", outline=None)
    image.save(f"{BACKGROUNDS_DIR}/square-{color[1].replace(' ', '-').lower()}.png")

def generate_header_backgrounds():
    for color in COLORS:
        generate_header_background(color)
