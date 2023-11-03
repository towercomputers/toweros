#!/usr/bin/env python3

import json
import os
import re
import sys
import subprocess
from base64 import b64encode

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

def run_cmd(cmd, to_json=False):
    out = subprocess.run(cmd, capture_output=True, encoding="UTF-8").stdout.strip()
    if to_json:
        return json.loads(out)
    return out

def get_mountpoints():
    all_devices = run_cmd(['lsblk', '-J'], to_json=True)
    mountpoints = {}
    for device in all_devices['blockdevices']:
        if device['type'] == 'disk':
            mountpoints[f"/dev/{device['name']}"] = device['mountpoints'][0]
    return mountpoints

def disk_list(exclude=None):
    all_disks = run_cmd(['lsscsi']).split("\n")
    mountpoints = get_mountpoints()
    disks = []
    for disk in all_disks:
        path = disk[disk.index('/dev/'):].split(" ")[0].strip()
        if exclude and path == exclude:
            continue
        if mountpoints[path] is not None:
            continue
        disks.append(disk)
    return disks

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
    
    salt = b64encode(os.urandom(16)).decode('utf-8')
    cmd = f"openssl passwd -6 -salt {salt} {password}"
    password_hash = run_cmd(cmd.split(" ")).split("\n")[0]
    
    return login, password_hash

def get_disk_encryption():
    print_title("Full disk encryption")
    return Confirm.ask("Do you want to encrypt the disk with a keyfile stored in an external device ?")

def get_target_drive():
    drive = select_value(
        disk_list(),
        "Please select the drive where you want to install TowerOS",
        "Target drive",
        no_columns=True
    )
    return drive[drive.index('/dev/'):].split(" ")[0].strip()

def check_secure_boot_status():
    sbctl_status = run_cmd(["sbctl", "status", "--json"], to_json=True)
    error = False
    if sbctl_status['secure_boot'] != False:
        print_error("Error: Secure boot is enabled, you must disable it to install TowerOS-Thinclient with secure boot.")
        error = True
    if sbctl_status['setup_mode'] != True:
        print_error("Error: Secure boot's 'Setup Mode' is disable, you must enbale it to install TowerOS-Thinclient with secure boot.")
        error = True
    if len(sbctl_status['vendors']) > 0:
        print_error("Error: You must delete all secure boot keys to install TowerOS-Thinclient with secure boot.")
        error = True
    if error:
        print_error("Please refer to the documentation to prepare your laptop firmware for secure boot:")
        print_error("https://github.com/towercomputers/toweros/blob/master/docs/SecureBoot.md")
        return False
    return True

def get_cryptkey_drive(os_target):
    no_selected_drives = disk_list(exclude=os_target)
    please_refresh = '<-- Let me insert a drive and refresh the list!'
    no_selected_drives.append(please_refresh)
    drive = select_value(
        no_selected_drives,
        "Please select the drive where you want to put the disk encryption keyfile",
        "Target keyfile drive",
        no_columns=True
    )
    if drive == please_refresh:
        return get_cryptkey_drive(os_target)
    else:
        return drive[drive.index('/dev/'):].split(" ")[0].strip()
    
def get_secure_boot():
    print_title("Secure boot")
    with_secure_boot = Confirm.ask("Do you want to install TowerOS-Thinclient with secure boot ?")
    if with_secure_boot and not check_secure_boot_status():
        continue_without_secure_boot = Confirm.ask("Do you want to continue without secure boot (y) or reboot (n) ?")
        if continue_without_secure_boot:
            return False
        else:
            os.system('reboot')
    return with_secure_boot

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

def get_startx_on_login():
    print_title("Start X on login")
    return Confirm.ask("Do you want to automatically start X on login ?")

def print_value(label, value):
    rprint(Text.assemble((f"{label}: ", "bold"), value))

def confirm_config(config):
    print_title("Please confirm the current configuration:")
    print_value("Target drive", config['TARGET_DRIVE'])
    print_value("Full Disk Encryption", config['ENCRYPT_DISK'])
    if config['ENCRYPT_DISK'] == "true":
        print_value("Cryptkey drive", config['CRYPTKEY_DRIVE'])
    print_value("Secure Boot", config['SECURE_BOOT'])
    print_value("Language", config['LANG'])
    print_value("Timezone", config['TIMEZONE'])
    print_value("Keyboard layout", config['KEYBOARD_LAYOUT'])
    print_value("Keyboard variant", config['KEYBOARD_VARIANT'])
    print_value("Username", config['USERNAME'])
    rprint("\n")
    print_error(f"Warning: The content of the device {config['TARGET_DRIVE']} will be permanently erased.")
    if config['ENCRYPT_DISK'] == "true":
        print_error(f"Warning: The content of the device {config['CRYPTKEY_DRIVE']} will be permanently erased.")
        print_error("Warning: The device containing the encryption key MUST be plugged in and your laptop's bios must be configured to boot on it.")
    if config['SECURE_BOOT'] == "true":
        print_error("Warning: You MUST enable the secure boot in your laptop firmware.")
        print_error("Warning: You MUST backup as soon as possible secure boot keys in /usr/share/secureboot/keys.")
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
        config['ENCRYPT_DISK'] = "true" if get_disk_encryption() else "false"
        if config['ENCRYPT_DISK'] == "true":
            config['CRYPTKEY_DRIVE'] = get_cryptkey_drive(config['TARGET_DRIVE'])
        config['SECURE_BOOT'] = "true" if get_secure_boot() else "false"
        config['LANG'] = get_lang()
        config['TIMEZONE'] = get_timezone()
        config['KEYBOARD_LAYOUT'], config['KEYBOARD_VARIANT'] = get_keymap()
        config['STARTX_ON_LOGIN'] = "true" if get_startx_on_login() else "false"
        config['USERNAME'], config['PASSWORD_HASH'] = get_user_information()
        config['ROOT_PASSWORD_HASH'] = config['PASSWORD_HASH']
        confirmed = confirm_config(config)
    return config

def main():
    config = "\n".join([f"{key}='{value}'" for key, value in ask_config().items()])
    with open("/root/tower.env", 'w') as fp:
        fp.write(config)
        fp.write("\n")
    return 0

if __name__ == '__main__':
    sys.exit(main())
