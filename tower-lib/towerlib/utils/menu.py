import os
import json
from io import StringIO

import sh
from sh import ssh, mkdir, sed, scp, mv

from towerlib.utils import clitask
from towerlib.sshconf import hosts, TOWER_DIR, get_hex_host_color

LABWC_DIR = os.path.expanduser('~/.config/labwc')

def get_installed_packages(host):
    apk_world = os.path.join(TOWER_DIR, 'hosts', host, 'world')
    if os.path.exists(apk_world):
        return open(apk_world, 'r').read().strip().split("\n")
    return []

def save_installed_packages(host, installed_packages):
    apk_world = os.path.join(TOWER_DIR, 'hosts', host, 'world')
    with open(apk_world, 'w') as fp:
        fp.write("\n".join(installed_packages))

def add_installed_package(host, package):
    # save package in host world
    installed_packages = get_installed_packages(host)
    if not (package in installed_packages):
        installed_packages.append(package)
        save_installed_packages(host, installed_packages)
    # update openbox menu
    prepare_openbox_menu()

def get_package_executables(host, package):
    executables = []
    for line in ssh(host, 'sudo', 'apk', 'info', '-qL', package, _iter=True):
        if line.strip().endswith('.desktop'):
            desktop_file_path = line.split(" ").pop().strip()
            if not desktop_file_path.startswith('/'): desktop_file_path = f"/{desktop_file_path}"
            desktop_file_content = ssh(host, 'cat', desktop_file_path).strip()
            executable, name, icon = None, None, ""
            for config_line in desktop_file_content.split("\n"):
                if config_line.startswith("Exec=") and not executable:
                    executable = config_line[5:].strip()
                if config_line.startswith("Name=") and not name:
                    name = config_line[5:].strip()
                if config_line.startswith("Icon=") and icon == "":
                    icon = config_line[5:].strip()
            if executable:
                executables.append({
                    'name': name,
                    'icon': icon,
                    'exec': executable
                })
    return executables

def get_host_executables(host):
    executables = []
    installed_packages = get_installed_packages(host)
    for package in installed_packages:
        executables.extend(get_package_executables(host, package))
    return executables

def generate_host_menu(host):
    # genereate host icon
    icon_path = '/var/towercomputers/labwc/circle_icon.svg'
    host_icon_path = os.path.join(LABWC_DIR, f'{host}_icon.svg')
    with open(icon_path, 'r') as fp:
        icon_content = fp.read()
        color = "#" + get_hex_host_color(host)
        host_icon = icon_content.replace('#000000', color)
    with open(host_icon_path, 'w') as fp:
        fp.write(host_icon)
    #generate host menu
    menu = StringIO()
    executables = get_host_executables(host)
    if len(executables) > 0:
        menu.write(f'<menu id="{host}_menu" label="{host}" icon="{host_icon_path}">')
        for executable in executables:
            menu.write(f'<item label="{executable["name"]}" icon="{executable["icon"]}">')
            menu.write(f'<action name="Execute" command="tower run {host} {executable["exec"]}" />')
            menu.write('</item>')
        menu.write('</menu>')
    return menu.getvalue()

def generate_hosts_menu():
    menu = StringIO()
    for host in hosts():
        menu.write(generate_host_menu(host))
    return menu.getvalue()

@clitask("Updating desktop menu...")
def prepare_openbox_menu():
    menu_template_path = '/var/towercomputers/labwc/menu.xml'
    with open(menu_template_path, 'r') as fp:
        menu_template = fp.read()
        tower_menus = generate_hosts_menu()
        openbox_menu = menu_template.replace('<!-- <TowerMenu /> -->', tower_menus)
        menu_path = os.path.join(LABWC_DIR, 'menu.xml')
        with open(menu_path, 'w') as fp:
            fp.write(openbox_menu)
