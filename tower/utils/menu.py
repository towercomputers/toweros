import os
import json

import sh
from sh import ssh, mkdir, sed, scp, mv

from tower.utils import clitask

def get_package_binaries(host, package):
    binaries = []
    for line in ssh(host, 'sudo', 'pacman', '-Ql', package, _iter=True):
        if '/bin/' in line and not line.strip().endswith('/'):
            binary = line.split(" ").pop().strip()
            binaries.append(binary)
    return binaries

@clitask("Copying desktop files from host to thinclient...")
def copy_desktop_files(host, package):
    for line in ssh(host, 'sudo', 'pacman', '-Ql', package, _iter=True):
        if line.strip().endswith('.desktop'):
            desktop_file_path = line.split(" ").pop().strip()
            desktop_folder, desktop_file_name = os.path.split(desktop_file_path)
            # prefix file with the host name
            locale_file_path = os.path.expanduser(f'~/{host}-{desktop_file_name}')
            # copy desktop file with in user directory
            scp(f"{host}:{desktop_file_path}", locale_file_path)
            # add `tower run <host>` in each Exec line.
            sed('-i', f's/Exec=/Exec=tower run {host} /g', locale_file_path)
            # prefix application name with host name
            sed('-i', f's/Name=/Name=[{host}] /g', locale_file_path)
            # with sudo copy .desktop file in the same folder as the host
            with sh.contrib.sudo(password="", _with=True):
                mkdir('-p', desktop_folder)
                mv(locale_file_path, desktop_folder)

@clitask("Updating fluxbox menu")
def generate_fluxbox_menu():
    menu_file = os.path.join(os.path.expanduser('~'), '.fluxbox', 'tower-menu')
    menu = open(menu_file, 'w')
    installed_packages = get_installed_packages()
    for host in installed_packages:
        menu.write(f"[submenu] ({host})\n")
        for package in installed_packages[host]:
            binaries = installed_packages[host][package]
            for binary in binaries:
                name = package if len(binaries) == 1 else os.path.basename(binary)
                menu.write(f"      [exec] ({name}) {{tower run {host} {binary}}}\n")
        menu.write("[end]\n")
    menu.close()

def get_installed_packages():
    json_file = os.path.join(os.path.expanduser('~'), '.config', 'tower', 'desktop.json')
    if os.path.exists(json_file):
        return json.load(open(json_file, 'r'))
    return {}

def save_installed_packages(installed_packages):
    conf_dir = os.path.join(os.path.expanduser('~'), '.config', 'tower')
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)
    json_file = os.path.join(conf_dir, 'desktop.json')
    json.dump(installed_packages, open(json_file, 'w'))
    generate_fluxbox_menu()

def add_installed_package(host, package):
    installed_packages = get_installed_packages()
    if host not in installed_packages:
        installed_packages[host] = {}
    binaries = get_package_binaries(host, package)
    if binaries:
        installed_packages[host][package] = binaries
        save_installed_packages(installed_packages)
        copy_desktop_files(host, package)
    