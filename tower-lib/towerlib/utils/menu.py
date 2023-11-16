import os
import json
from io import StringIO

import sh
from sh import ssh, mkdir, sed, scp, mv

from towerlib.utils import clitask
from towerlib.sshconf import hosts, TOWER_DIR

@clitask("Copying desktop files from host to thinclient...")
def copy_desktop_files(host, package):
    for line in ssh(host, 'sudo', 'apk', 'info', '-qL', package, _iter=True):
        if line.strip().endswith('.desktop'):
            desktop_file_path = line.split(" ").pop().strip()
            if not desktop_file_path.startswith('/'):
                desktop_file_path = f"/{desktop_file_path}"
            desktop_folder, desktop_file_name = os.path.split(desktop_file_path)
            # prefix file with the host name
            locale_file_path = os.path.expanduser(f'~/{host}-{desktop_file_name}')
            # copy desktop file with in user directory
            scp(f"{host}:{desktop_file_path}", locale_file_path)
            # add `tower run <host>` in each Exec line.
            sed('-i', f's/Exec=/Exec=tower run {host} /g', locale_file_path)
            # update application categories
            sed('-i', f's/Categories=/Categories=X-tower-{host};/g', locale_file_path)
            # with sudo copy .desktop file in the same folder as the host
            with sh.contrib.sudo(password="", _with=True):
                mkdir('-p', desktop_folder)
                mv(locale_file_path, desktop_folder)

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
    # update desktop shortcuts
    copy_desktop_files(host, package)

def restore_installed_packages():
    for host in hosts():
        installed_packages = get_installed_packages(host)
        for package in installed_packages:
            copy_desktop_files(host, package)

@clitask("Updating xfce menu...")
def prepare_xfce_menu():
    INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'toweros-installers', 'toweros-thinclient')
    # create local directories
    directories_folder = os.path.expanduser('~/.local/share/desktop-directories/')
    menu_folder = os.path.expanduser('~/.config/menus/')
    mkdir('-p', directories_folder)
    mkdir('-p', menu_folder)
    # prepare desktop-directories folder
    for hostindex, hostname in enumerate(hosts()):
        # genereate host icon
        colors = ["#fff100", "#ff8c00", "#e81123", "#ec008c", "#68217a", "#00188f", "#00bcf2", "#00b294", "#009e49", "#bad80a"]
        icon_path = os.path.join(INSTALLER_DIR, 'xfce', f'circle_icon.svg')
        host_icon_path = os.path.join(directories_folder, f'{hostname}_icon.svg')
        with open(icon_path, 'r') as fp:
            icon_content = fp.read()
            color = colors[hostindex % len(colors)]
            host_icon = icon_content.replace('#000000', color)
        with open(host_icon_path, 'w') as fp:
            fp.write(host_icon)
        # generate host directory file
        tower_directory_path = os.path.join(directories_folder, f'tower-{hostname}.directory')
        with open(tower_directory_path, 'w') as tower_directory:
            tower_directory.write('[Desktop Entry]\n')
            tower_directory.write('Version=1.0\n')
            tower_directory.write('Type=Directory\n')
            tower_directory.write(f'Icon={host_icon_path}\n')
            tower_directory.write(f'Name=Host: {hostname}\n')
            tower_directory.write(f'Comment=Applications installed in {hostname} host\n')
    # prepare tower.menu file
    tower_menu_path = os.path.join(menu_folder, 'tower.menu')
    with open(tower_menu_path, 'w') as tower_menu_xml:
        tower_menu_xml.write('<Menu>')
        for hostname in hosts():
            tower_menu_xml.write('<Menu>')
            tower_menu_xml.write(f'<Name>Tower {hostname}</Name>')
            tower_menu_xml.write(f'<Directory>tower-{hostname}.directory</Directory>')
            tower_menu_xml.write(f'<Include><Category>X-tower-{hostname}</Category></Include>')
            tower_menu_xml.write('</Menu>')
        tower_menu_xml.write('</Menu>')
    # prepare xfce-applications.menu file
    xfce_menu_template_path = os.path.join(INSTALLER_DIR, 'xfce', 'xfce-applications.menu.tmpl')
    with open(xfce_menu_template_path, 'r') as fp:
        xfce_menu_template = fp.read()
        tower_menus = ""
        for hostname in hosts():
            tower_menus = f"{tower_menus}<Menuname>Tower {hostname}</Menuname>"
        xfce_menu = xfce_menu_template.replace('<!-- <TowerMenu /> -->', tower_menus)
    xfce_applicaton_menu_path =  os.path.join(menu_folder, 'xfce-applications.menu')
    with open(xfce_applicaton_menu_path, 'w') as xfce_applicaton_menu:
        xfce_applicaton_menu.write(xfce_menu)