import logging
import sys
import time
import signal

from rich.prompt import Confirm
from rich.text import Text
from rich import print as rprint

from towerlib.utils.shell import ssh, scp, rm, Command, ErrorReturnCode
from towerlib.utils import clitask
from towerlib.utils.menu import copy_desktop_files
from towerlib.sshconf import is_online_host, get_saved_packages
from towerlib.utils.exceptions import LockException, TowerException
from towerlib import sshconf, config

logger = logging.getLogger('tower')
APK_REPOS_HOST = "dl-cdn.alpinelinux.org"
APK_REPOS_URL = [
    f"http://{APK_REPOS_HOST}/alpine/{config.HOST_ALPINE_BRANCH}/main",
    f"http://{APK_REPOS_HOST}/alpine/{config.HOST_ALPINE_BRANCH}/community",
]
LOCAL_TUNNELING_PORT = 8666

signal.signal(signal.SIGTRAP, signal.default_int_handler)
signal.signal(signal.SIGHUP, signal.default_int_handler)

def sprint(value):
    print(value.decode("utf-8", 'ignore') if isinstance(value, bytes) else value, end='', flush=True)


def offline_cmd(host, cmd):
    if host == 'thinclient':
        Command('sh')('-c', cmd)
    else:
        ssh(host, cmd)


@clitask("Preparing installation...")
def prepare_offline_host(host):
    # add repo host in /etc/hosts
    offline_cmd(host, 'sudo cp /etc/hosts /etc/hosts.bak')
    offline_cmd(host, f"echo '127.0.0.1 {APK_REPOS_HOST}\n' | sudo tee /etc/hosts")
    # add iptables rule to redirect http requests to port
    tunnel_port = LOCAL_TUNNELING_PORT if host == 'thinclient' else 4443
    offline_cmd(host, f"sudo iptables -t nat -A OUTPUT -p tcp -m tcp --dport 80 -j REDIRECT --to-ports {tunnel_port}")


def cleanup_offline_host(host):
    # restore /etc/hosts
    offline_cmd(host, "sudo mv /etc/hosts.bak /etc/hosts")
    # clean iptables
    # sudo iptables -t nat -D OUTPUT $(sudo iptables -nvL -t nat --line-numbers | grep -m 1 '443 redir ports 4443' | awk '{print $1}'
    offline_cmd(host, "sudo iptables -t nat -F")


def kill_ssh():
    killcmd = f"ps -ax | grep '{LOCAL_TUNNELING_PORT}:{APK_REPOS_HOST}:80' | grep -v grep | awk '{{print $1}}' | xargs kill 2>/dev/null || true"
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
            copy_desktop_files(host, package)
    except ErrorReturnCode as exc:
        raise TowerException(f"Error while installing packages in {host}") from exc

def open_router_tunnel():
    # run ssh tunnel with router host in background
    ssh(
        '-L', f"{LOCAL_TUNNELING_PORT}:{APK_REPOS_HOST}:80", '-N',
        config.ROUTER_HOSTNAME,
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
                f"sudo apk --progress -v add {' '.join(packages)}",
                _err=sprint, _out=sprint, _in=sys.stdin,
                _out_bufsize=0, _err_bufsize=0,
            )
        except ErrorReturnCode:
            error = True # error in remote host is already displayed
        if not error:
            for package in packages:
                copy_desktop_files(host, package)
    finally:
        cleanup(host)
        if error:
            raise TowerException(f"Error while installing packages in {host}")


@clitask("Installing {0} in thin client...", task_parent=True)
def install_in_thinclient(packages):
    error = False
    try:
        prepare_offline_host("thinclient")
        open_router_tunnel()
        logger.info("Running apk in thinclient...")
        try:
            apk_cmd = f"sudo apk --progress add {' '.join(packages)}"
            Command('sh')('-c',
                apk_cmd,
                _err_to_out=True, _out=sprint, _in=sys.stdin,
                _out_bufsize=0, _err_bufsize=0,
            )
        except ErrorReturnCode:
            error = True # error in remote host is already displayed
    finally:
        cleanup("thinclient")
        if error:
            raise TowerException("Error while installing packages in thin client")


def can_install(host):
    if host != "thinclient" and not sshconf.is_up(host):
        raise TowerException(f"`{host}` is down. Please start it first.")
    if (host == "thinclient" or not sshconf.is_online_host(host)) and not sshconf.exists(config.ROUTER_HOSTNAME):
        raise TowerException(f"`{host}` is an offline host and `{config.ROUTER_HOSTNAME}` host was not found. Please provision it first.")


def display_install_warning(host):
    if host == 'thinclient':
        confirmation = Text("This is a *dangerous operation*. Packages should normally be installed only on hosts. Are you sure you want to install this package directly on the thin client?", style='red')
        if not Confirm.ask(confirmation):
            return
    if host == 'router':
        confirmation = Text("This is a *dangerous operation*. Packages should normally be installed only on other hosts. Are you sure you want to install this package on the router?", style='red')
        if not Confirm.ask(confirmation):
            return


def install_packages(host, packages):
    can_install(host)
    display_install_warning(host)
    if host == 'thinclient':
        install_in_thinclient(packages)
    elif is_online_host(host):
        install_in_online_host(host, packages)
    else:
        install_in_offline_host(host, packages)


def reinstall_all_packages(host):
    can_install(host)
    packages = get_saved_packages(host)
    if packages:
        install_packages(host, packages)


@clitask("Opening APK tunnel with {0}...", task_parent=True)
def open_apk_tunnel(host):
    if host != "thinclient" and sshconf.is_online_host(host):
        raise TowerException(f"`{host}` is an online host. You can use `apk` command directly in `{host}`.")
    can_install(host)
    display_install_warning(host)
    try:
        prepare_offline_host(host)
        open_router_tunnel()
        if host != "thinclient":
            ssh('-R', f'4443:127.0.0.1:{LOCAL_TUNNELING_PORT}', '-N', host, _bg=True, _bg_exc=False)
        message = f"APK tunnel opened. You can use `apk` command in host `{host}` with `ssh {host} sudo apk ...`.\nPress Ctrl+C to close it."
        rprint(Text(message, style="green bold"))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(host)
