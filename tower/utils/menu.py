import os
import json
from io import StringIO

import sh
from sh import ssh, mkdir, sed, scp, mv

from tower.utils import clitask
from tower.sshconf import hosts

def get_package_binaries(host, package):
    binaries = []
    for line in ssh(host, 'sudo', 'apk', 'info', '-qL', package, _iter=True):
        if '/bin/' in line and not line.strip().endswith('/'):
            binary = line.split(" ").pop().strip()
            if not binary.startswith('/'):
                binary = f"/{binary}"
            binaries.append(binary)
    return binaries

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

def add_installed_package(host, package):
    installed_packages = get_installed_packages()
    if host not in installed_packages:
        installed_packages[host] = {}
    binaries = get_package_binaries(host, package)
    if binaries:
        installed_packages[host][package] = binaries
        save_installed_packages(installed_packages)
        copy_desktop_files(host, package)

@clitask("Updating xfce menu...")
def prepare_xfce_menu():
    INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts', 'toweros-thinclient')
    # create local directories
    directories_folder = os.path.expanduser('~/.local/share/desktop-directories/')
    menu_folder = os.path.expanduser('~/.config/menus/')
    mkdir('-p', directories_folder)
    mkdir('-p', menu_folder)
    # prepare desktop-directories folder
    for hostindex, hostname in enumerate(hosts()):
        # genereate host icon
        colors = ["#fff100", "#ff8c00", "#e81123", "#ec008c", "#68217a", "#00188f", "#00bcf2", "#00b294", "#009e49", "#bad80a"]
        icon_path = os.path.join(INSTALLER_DIR, f'circle_icon.svg')
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
    xfce_menu_template_path = os.path.join(INSTALLER_DIR, 'xfce-applications.menu.tmpl')
    with open(xfce_menu_template_path, 'r') as fp:
        xfce_menu_template = fp.read()
        tower_menus = ""
        for hostname in hosts():
            tower_menus = f"{tower_menus}<Menuname>Tower {hostname}</Menuname>"
        xfce_menu = xfce_menu_template.replace('<!-- <TowerMenu /> -->', tower_menus)
    xfce_applicaton_menu_path =  os.path.join(menu_folder, 'xfce-applications.menu')
    with open(xfce_applicaton_menu_path, 'w') as xfce_applicaton_menu:
        xfce_applicaton_menu.write(xfce_menu)