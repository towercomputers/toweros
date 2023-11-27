import os

from sh import ssh, mkdir, sed, scp, mv, Command

from towerlib.utils.decorators import clitask
from towerlib.utils.sh import sh_sudo
from towerlib.sshconf import get_host_color_name
from towerlib.config import TOWER_DIR, DESKTOP_FILES_DIR

@clitask("Copying desktop files from host to thinclient...")
def copy_desktop_files(host, package):
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
