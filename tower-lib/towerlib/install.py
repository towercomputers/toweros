import os
import logging
import sys
import time

from rich.prompt import Confirm
from rich.text import Text
from sh import ssh, scp, rm, Command, ErrorReturnCode

from towerlib.utils import clitask
from towerlib.utils.menu import add_installed_package, get_installed_packages
from towerlib.sshconf import ROUTER_HOSTNAME, is_online_host
from towerlib.utils.exceptions import LockException, TowerException
from towerlib import sshconf

logger = logging.getLogger('tower')

APK_REPOS_HOST = "dl-cdn.alpinelinux.org"
APK_REPOS_URL = [
    f"http://{APK_REPOS_HOST}/alpine/latest-stable/main",
    f"http://{APK_REPOS_HOST}/alpine/latest-stable/community",
]
LOCAL_TUNNELING_PORT = 8666

def sprint(value):
    print(value.decode("utf-8", 'ignore') if isinstance(value, bytes) else value, end='', flush=True)

def prepare_repositories_file(host):
    file_name = os.path.join(os.path.expanduser('~'), f'repositories.offline.{host}')
    # use temporary file as lock file
    if os.path.exists(file_name):
        raise LockException(f"f{file_name} already exists! Is another install in progress? If not, delete this file and try again.")
    # generate temporary apk repositories
    with open(file_name, 'w', encoding="UTF-8") as fp:
        for repo in APK_REPOS_URL:
            fp.write(f"{repo}\n")
    # copy apk repositories in offline host
    if host != 'thinclient':
        scp(file_name, f"{host}:~/")
        rm('-f', file_name)

def offline_cmd(host, cmd):
    if host == 'thinclient':
        Command('sh')('-c', cmd)
    else:
        ssh(host, cmd)

@clitask("Preparing installation...")
def prepare_offline_host(host):
    # prepare apk repositories in offline host
    prepare_repositories_file(host)
    # add repo host in /etc/hosts
    offline_cmd(host, 'sudo cp /etc/hosts /etc/hosts.bak')
    offline_cmd(host, f"echo '127.0.0.1 {APK_REPOS_HOST}\n' | sudo tee /etc/hosts")
    # add iptables rule to redirect http requests to port
    tunnel_port = LOCAL_TUNNELING_PORT if host == 'thinclient' else 4443
    offline_cmd(host, f"sudo iptables -t nat -A OUTPUT -p tcp -m tcp --dport 80 -j REDIRECT --to-ports {tunnel_port}")

def cleanup_offline_host(host):
    # remove temporary apk repositories in thinclient
    file_name = f'~/repositories.offline.{host}'
    if host == 'thinclient':
        file_name = os.path.expanduser(file_name)
    offline_cmd(host, f"rm -f {file_name}")
    # restore /etc/hosts
    offline_cmd(host, "sudo mv /etc/hosts.bak /etc/hosts")
    # clean iptables
    # sudo iptables -t nat -D OUTPUT $(sudo iptables -nvL -t nat --line-numbers | grep -m 1 '443 redir ports 4443' | awk '{print $1}'
    offline_cmd(host, "sudo iptables -t nat -F")

def kill_ssh():
    killcmd = f"ps -ef | grep '{LOCAL_TUNNELING_PORT}:{APK_REPOS_HOST}:80' | grep -v grep | awk '{{print $1}}' | xargs kill 2>/dev/null || true"
    #print(killcmd)
    Command('sh')('-c', killcmd)

@clitask("Cleaning up...")
def cleanup(host):
    kill_ssh()
    cleanup_offline_host(host)

@clitask("Installing {1} in {0}...", task_parent=True)
def install_in_online_host(host, packages):
    # we just need to run apk with ssh...
    try:
        ssh(
            '-t', host,
            f"sudo apk add --progress {' '.join(packages)}",
            _err=sprint, _out=sprint, _in=sys.stdin,
            _out_bufsize=0, _err_bufsize=0,
        )
        for package in packages:
            add_installed_package(host, package)
    except ErrorReturnCode:
        pass # error in remote host is already displayed

def open_router_tunnel():
    # run ssh tunnel with router host in background
    ssh(
        '-L', f"{LOCAL_TUNNELING_PORT}:{APK_REPOS_HOST}:80", '-N',
        ROUTER_HOSTNAME,
        _err_to_out=True, _out=logger.debug, _bg=True, _bg_exc=False
    )
    # wait for ssh tunnel to be ready
    time.sleep(1)

@clitask("Installing {1} in {0}...", task_parent=True)
def install_in_offline_host(host, packages):
    try:
        prepare_offline_host(host)
        open_router_tunnel()
        logger.info("Running apk in %s...", host)
        error = False
        try:
            # open the second ssh tunnel with the offline host and run `apk add`
            ssh(
                '-R', f'4443:127.0.0.1:{LOCAL_TUNNELING_PORT}', '-t',
                host,
                f"sudo apk --repositories-file ~/repositories.offline.{host} --progress add {' '.join(packages)}",
                _err=sprint, _out=sprint, _in=sys.stdin,
                _out_bufsize=0, _err_bufsize=0,
            )
        except ErrorReturnCode:
            error = True # error in remote host is already displayed
        if not error:
            for package in packages:
                add_installed_package(host, package)
    finally:
        cleanup(host)

@clitask("Installing {0} in Thin Client...", task_parent=True)
def install_in_thinclient(packages):
    try:
        prepare_offline_host("thinclient")
        open_router_tunnel()
        logger.info("Running apk in thinclient...")
        try:
            repo_file = os.path.expanduser('~/repositories.offline.thinclient')
            apk_cmd = f"sudo apk --repositories-file {repo_file} --progress add {' '.join(packages)}"
            Command('sh')('-c',
                apk_cmd,
                _err_to_out=True, _out=sprint, _in=sys.stdin,
                _out_bufsize=0, _err_bufsize=0,
            )
        except ErrorReturnCode:
            pass # error in remote host is already displayed
    finally:
        cleanup("thinclient")

def can_install(host):
    if not sshconf.is_up(host):
        raise TowerException(message=f"`{host}` is down. Please start it first.")
    if (host == "thinclient" or not sshconf.is_online_host(host)) and not sshconf.exists(sshconf.ROUTER_HOSTNAME):
        raise TowerException(message=f"`{host}` is an offline host and `{sshconf.ROUTER_HOSTNAME}` host was not found. Please provision it first.")

def install_packages(host, packages):
    can_install(host)
    if host == 'thinclient':
        confirmation = Text("This is a *dangerous operation* and only rarely necessary. Packages should normally be installed only on hosts. Are you sure you want to install a package directly on the thin client?", style='red')
        if not Confirm.ask(confirmation):
            return
    if host == 'router':
        confirmation = Text("This is a *dangerous operation* and only rarely necessary. Packages should normally be installed only on other hosts. Are you sure you want to install a package directly on the router?", style='red')
        if not Confirm.ask(confirmation):
            return
    if host == 'thinclient':
        install_in_thinclient(packages)
    elif is_online_host(host):
        install_in_online_host(host, packages)
    else:
        install_in_offline_host(host, packages)

@clitask("Re-installing all packages on {0}...", task_parent=True)
def reinstall_all_packages(host):
    can_install(host)
    packages = get_installed_packages(host)
    if packages:
        install_packages(host, packages)
