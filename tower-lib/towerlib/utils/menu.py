import os

from sh import ssh, mkdir, sed, scp, mv, Command

from towerlib.utils.decorators import clitask
from towerlib.sshconf import get_host_color_name, hosts
from towerlib.config import TOWER_DIR, DESKTOP_FILES_DIR

def restart_sfwbar():
    Command('sh')('-c', "killall sfwbar || true")
    Command('sh')('-c', "sfwbar", _bg=True, _bg_exc=False)

@clitask("Copying desktop files from host to thinclient...")
def copy_desktop_files(host, package):
    with_icons = False
    for line in ssh(host, 'sudo', 'apk', 'info', '-qL', package, _iter=True):
        if line.strip().endswith('.desktop'):
            desktop_file_path = line.split(" ").pop().strip()
            if not desktop_file_path.startswith('/'):
                desktop_file_path = f"/{desktop_file_path}"
            desktop_file_name = os.path.basename(desktop_file_path)
            # prefix file with the host name
            locale_file_path = os.path.expanduser(f'~/{host}-{desktop_file_name}')
            # copy desktop file with in user directory
            scp(f"{host}:{desktop_file_path}", locale_file_path)
            # add `tower run <host>` in each Exec line.
            sed('-i', f's/Exec=/Exec=tower run {host} /g', locale_file_path)
            # update application categories
            sed('-i', f's/Categories=/Categories=X-tower-{host};/g', locale_file_path)
            Command('sh')('-c', f"echo 'Color={get_host_color_name(host)}' >> {locale_file_path}")
            # copy .desktop file in user specific applications folder
            mkdir('-p', DESKTOP_FILES_DIR)
            mv(locale_file_path, DESKTOP_FILES_DIR)
        share_icon_folder = 'share/icons/hicolor/'
        if share_icon_folder in line:
            # copy icons from hosts to thinclient
            host_icon_full_path = '/' + line.strip()
            host_icon_short_path = host_icon_full_path[host_icon_full_path.find(share_icon_folder) + len(share_icon_folder):]
            host_icon_local_path = os.path.expanduser(f'~/.local/{share_icon_folder}{host_icon_short_path}')
            mkdir('-p', os.path.dirname(host_icon_local_path))
            scp('-r', f"{host}:{host_icon_full_path}", host_icon_local_path)
            with_icons = True
    if with_icons:
        # update icon cache
        Command('sh')('-c', f"gtk-update-icon-cache -f -t ~/.local/{share_icon_folder} || true")
        Command('sh')('-c', f"gtk-update-icon-cache -f -t /usr/{share_icon_folder} || true")
        restart_sfwbar()

def get_installed_packages(host):
    apk_world = os.path.join(TOWER_DIR, 'hosts', host, 'world')
    if os.path.exists(apk_world):
        return open(apk_world, 'r', encoding="UTF-8").read().strip().split("\n")
    return []

def save_installed_packages(host, installed_packages):
    apk_world = os.path.join(TOWER_DIR, 'hosts', host, 'world')
    with open(apk_world, 'w', encoding="UTF-8") as fp:
        fp.write("\n".join(installed_packages))

def add_installed_package(host, package):
    # save package in host world
    installed_packages = get_installed_packages(host)
    if package not in installed_packages:
        installed_packages.append(package)
        save_installed_packages(host, installed_packages)
    # copy desktop files from host to thinclient
    copy_desktop_files(host, package)

@clitask("Generate sfwbar widget...")
def generate_tower_widget():
    hosts_status = []
    for host in hosts():
        hosts_status.append(f"{host}_status = RegEx('^{host}=(green|red)$')")
    hosts_status = "\n".join(hosts_status)
    status_path = os.path.join(TOWER_DIR, 'status')
    widget_scanner = f"""
scanner {{
  File('{status_path}') {{
    {hosts_status}
  }}
}}
"""
    layouts = []
    for host in hosts():
        layouts.append(f"""
layout {{
  label {{
    interval = 1000
    style = 'LabelStyle'
    value = '{host}'
  }}
  image {{
    style = 'CircleStyle'
    value = 'circle-' + ${host}_status
  }}
}}
""")
    layouts = "\n".join(layouts)
    styles = """
#CSS

#LabelStyle {
    padding: 5px;
    padding-top: 8px;
    padding-right: 2px;
}

#CircleStyle {
    padding: 5px;
    padding-top: 8px;
    padding-left:0;
}
"""
    widget = f"{widget_scanner}\n{layouts}\n{styles}"
    widget_path = f"{TOWER_DIR}/tower.widget"
    with open(widget_path, 'w', encoding="UTF-8") as fp:
        fp.write(widget)
    restart_sfwbar()
