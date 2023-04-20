import os
import json
from io import StringIO

from sh import ssh

def get_package_binaries(host, package):
    binaries = []
    for line in ssh(host, 'sudo', 'pacman', '-Ql', package, _iter=True):
        if '/bin/' in line and not line.strip().endswith('/'):
            binary = line.split(" ").pop().strip()
            binaries.append(binary)
    return binaries

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
    json_file = os.path.join(os.path.expanduser('~'), '.config', 'tower', 'tower-menu.json')
    if os.path.exists(json_file):
        return json.load(open(json_file, 'r'))
    return {}

def save_installed_packages(installed_packages):
    conf_dir = os.path.join(os.path.expanduser('~'), '.config', 'tower')
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)
    json_file = os.path.join(conf_dir, 'tower-menu.json')
    json.dump(installed_packages, open(json_file, 'w'))
    generate_fluxbox_menu()

def add_installed_package(host, package):
    installed_packages = get_installed_packages()
    if host not in installed_packages:
        installed_packages[host] = {}
    binaries = get_package_binaries(host, package)
    if not binaries:
        raise Exception(f"No binary found for the package `{package}`")
    installed_packages[host][package] = binaries
    save_installed_packages(installed_packages)
    