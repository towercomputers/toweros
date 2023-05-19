#!/usr/bin/env python3

import json
import os
import re
import sys
import subprocess

from rich import print as rprint
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.console import Console

#from sh import lsscsi, figlet

LOCALE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale.json')
with open(LOCALE_FILE, "r") as fp:
    LOCALE = json.load(fp)

TIMEZONES = LOCALE["timezones"]
KEYBOARDS = LOCALE["keyboards"]
LANGS = LOCALE["langs"]
#DRIVES = lsscsi('-s').strip().split("\n")
DRIVES = subprocess.run(['lsscsi'],capture_output=True, encoding="UTF-8").stdout.strip().split("\n")

def print_title(title):
    title_text = Text(f"\n{title}\n")
    title_text.stylize("bold purple")
    rprint(title_text)

def print_error(text):
    error_text = Text(text)
    error_text.stylize("bold red")
    rprint(error_text)

def select_value(values, title, ask, clean_values='', no_columns=False):
    if title:
        print_title(title)
    else:
        print()
    choices = [f"({i + 1}) {r.replace(clean_values, '')}" for i, r in enumerate(values)]
    if no_columns:
        for value in choices:
            rprint(value)
        print()
    else:
        columns = Columns(choices, equal=True, expand=True, column_first=True)
        rprint(columns, "")
    ask_text = Text(f"{ask} [1-{len(choices)}]")
    ask_text.stylize("bold")
    valid_choices = [f"{i + 1}" for i in range(len(choices))]
    choice_num = None
    while choice_num not in valid_choices:
        choice_num = Prompt.ask(ask_text)
    choice = values[int(choice_num) - 1]
    return choice

def select_sub_value(values, title, ask, sub_values, sub_ask, back_text):
    value1 = select_value(values, title, ask)
    if value1 in sub_values:
        choices = [*sub_values[value1], f'<-- {back_text}']
        value2 = select_value(choices, None, sub_ask)
        if value2 == f'<-- {back_text}':
            return select_sub_value(values, title, ask, sub_values, sub_ask, back_text)
    else:
        value2 = ""
    return [value1, value2]

def select_by_letter(title, ask1, ask2, values):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    print_title(title)
    letter = "0"
    while letter not in letters:
        ask_text = Text(f"{ask1} [a-z]")
        ask_text.stylize("bold")
        letter = Prompt.ask(ask_text)
    selected_values = [*[v for v in values if v[0] == letter], '<-- Select another letter']
    value = select_value(selected_values, None, ask2, clean_values='.UTF-8')
    if value == '<-- Select another letter':
        return select_by_letter(title, ask1, ask2, values)
    return value

def get_user_information():
    print_title("Please enter the first user information")
    login = ""
    retry = 0
    while re.match(r'^[a-zA-Z0-0_-]{3,32}$', login) is None:
        if retry:
            print_error("Incorrect login, please retry.")
        login = Prompt.ask("Enter the username (between 3 and 32 alphanumerics characters):", default="tower")
        retry += 1
    password = ""
    confirm_password = ""
    retry = 0
    while password == "" or password != confirm_password:
        if retry:
            print_error("Incorrect password, please retry.")
        password = Prompt.ask("Enter the password", password=True)
        confirm_password = Prompt.ask("Confirm the password", password=True)
        retry += 1
    return login, password

def get_target_drive():
    drive = select_value(
        DRIVES,
        "Please select the drive where you want to install TowerOS",
        "Target drive",
        no_columns=True
    )
    return drive[drive.index('/dev/'):].split(" ")[0].strip()

def get_lang():
    return select_by_letter(
        "Please select your language:", 
        "Enter the first letter of your lang",
        "Enter the number of your lang",
        LANGS
    )

def get_timezone():
    return "/".join(select_sub_value(
        TIMEZONES["regions"], 
        "Please select the region of your timezone:", 
        "Enter the number of your region",
        TIMEZONES["zonesByRegions"],
        "Enter the number of your zone",
        "Select another region"
    ))

def get_keymap():
    layout, variant = select_sub_value(
        KEYBOARDS["layouts"],
        "Please select the layout of your keyboard:",
        "Enter the number of your keyboard layout",
        KEYBOARDS["variantsByLayout"],
        "Enter the number of your keyboard variant",
        "Select another layout"
    )
    variant = layout if variant == "No Variant" else f"{layout}-{variant}"
    return layout, variant

def print_value(label, value):
    rprint(Text.assemble((f"{label}: ", "bold"), value))

def confirm_config(config):
    print_title("Please confirm the current configuration:")
    print_value("Target drive", config['TARGET_DRIVE'])
    print_value("Language", config['LANG'])
    print_value("Timezone", config['TIMEZONE'])
    print_value("Keyboard layout", config['KEYBOARD_LAYOUT'])
    print_value("Keyboard variant", config['KEYBOARD_VARIANT'])
    print_value("Username", config['USERNAME'])
    return Confirm.ask("\nIs the configuration correct?")

def ask_config():
    Console().clear()
    title = subprocess.run(
        ['figlet', '-w', '160', 'TowerOS-ThinClient'], 
        capture_output=True, encoding="UTF-8"
    ).stdout
    print(title)
    #figlet('-w', 160, 'TowerOS-ThinClient', _out=sys.stdin)
    confirmed = False
    config = {}
    while not confirmed:
        config['TARGET_DRIVE'] = get_target_drive()
        config['LANG'] = get_lang()
        config['TIMEZONE'] = get_timezone()
        config['KEYBOARD_LAYOUT'], config['KEYBOARD_VARIANT'] = get_keymap()
        config['USERNAME'], config['PASSWORD'] = get_user_information()
        config['ROOT_PASSWORD'] = config['PASSWORD']
        confirmed = confirm_config(config)
    return config

def main():
    config = "\n".join([f'{key}="{value}"' for key, value in ask_config().items()])
    with open("/root/tower.env", 'w') as fp:
        fp.write(config)
        fp.write("\n")
    return 0

if __name__ == '__main__':
    sys.exit(main())
