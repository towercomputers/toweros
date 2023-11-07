import os
import logging
import sys
from urllib.parse import urlparse
import time

from sh import ssh, scp, rm, Command, ErrorReturnCode, apk

from towerlib.utils import clitask
from towerlib.utils.menu import add_installed_package
from towerlib.sshconf import ROUTER_HOSTNAME, is_online_host

logger = logging.getLogger('tower')

APK_REPOS_HOST = "dl-cdn.alpinelinux.org"
APK_REPOS_URL = [
    f"http://{APK_REPOS_HOST}/alpine/latest-stable/main",
    f"http://{APK_REPOS_HOST}/alpine/latest-stable/community",
]

LOCAL_TUNNELING_PORT = 8666

sprint = lambda str: print(str.decode("utf-8", 'ignore') if isinstance(str, bytes) else str, end='', flush=True)

def prepare_repositories_file(host):
    file_name = os.path.join(os.path.expanduser('~'), f'repositories.offline.{host}')
    # use temporary file as lock file
    if os.path.exists(file_name):
        raise Exception(f"f{file_name} already exists! Is another install in progress? if not, delete this file and try again.")
    # generate temporary apk repositories 
    with open(file_name, 'w') as fp:
        for repo in APK_REPOS_URL:
            fp.write(f"{repo}\n")
    # copy apk repositories in offline host
    if host != 'thinclient':
        scp(file_name, f"{host}:~/")

@clitask("Preparing installation...")
def prepare_offline_host(host):
    # prepare apk repositories in offline host
    prepare_repositories_file(host)
    if host == 'thinclient':
        # add repo host in /etc/hosts
        Command('sh')('-c', f"echo '127.0.0.1 {APK_REPOS_HOST}' | sudo tee -a /etc/hosts")
        # add iptables rule to redirect https requests to port 4443
        Command('sh')('-c', f"sudo iptables -t nat -A OUTPUT -p tcp -m tcp --dport 80 -j REDIRECT --to-ports {LOCAL_TUNNELING_PORT}")
    else:
        # add repo host in /etc/hosts
        ssh(host, f"echo '127.0.0.1 {APK_REPOS_HOST}' | sudo tee -i /etc/hosts")
        # add iptables rule to redirect https requests to port 4443
        ssh(host, "sudo iptables -t nat -A OUTPUT -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 4443")

def cleanup_offline_host(host):
    # remove temporary apk repositories
    file_name = os.path.join(os.path.expanduser('~'), f'repositories.offline.{host}')
    rm('-f', file_name)
    if host == 'thinclient':
        # clean /etc/hosts
        Command('sh')('-c', f"sudo sed -i '/{APK_REPOS_HOST}/d' /etc/hosts")
        # clean iptables
        Command('sh')('-c', "sudo iptables -t nat -F")
    else:
        ssh(host, f"rm -f ~/{os.path.basename(file_name)}")
        # clean /etc/hosts
        ssh(host, f"sudo sed -i '/{APK_REPOS_HOST}/d' /etc/hosts")
        # clean iptables
        #ssh(host, "sudo iptables -t nat -D OUTPUT $(sudo iptables -nvL -t nat --line-numbers | grep -m 1 '443 redir ports 4443' | awk '{print $1}')")
        ssh(host, "sudo iptables -t nat -F")

def kill_ssh():
    killcmd = f"ps -ef | grep '{LOCAL_TUNNELING_PORT}:{APK_REPOS_HOST}:80' | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"
    #print(killcmd)
    Command('sh')('-c', killcmd)

@clitask("Cleaning up...")
def cleanup(host):
    kill_ssh()
    cleanup_offline_host(host)

@clitask("Installing {1} in {0}...", task_parent=True)
def install_in_offline_host(host, packages):
    try:
        # prepare offline host
        prepare_offline_host(host)
        # run ssh tunnel with online host in background
        ssh(
            '-L', f"{LOCAL_TUNNELING_PORT}:{APK_REPOS_HOST}:80", '-N', '-v',
            ROUTER_HOSTNAME,
            _err_to_out=True, _out=logger.debug, _bg=True, _bg_exc=False
        )
        # run apk in offline host
        logger.info(f"Running apk in {host}...")
        error = False
        try:
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

@clitask("Installing {0} in Thin Client...", task_parent=True)
def install_in_thinclient(packages):
    try:
        prepare_offline_host("thinclient")
        # run ssh tunnel with router host in background
        ssh(
            '-L', f"{LOCAL_TUNNELING_PORT}:{APK_REPOS_HOST}:80", '-N',
            ROUTER_HOSTNAME,
            _err_to_out=True, _out=logger.debug, _bg=True, _bg_exc=False
        )
        # wait for ssh tunnel to be ready
        time.sleep(1)
        # run apk in thinclient
        error = False
        try:
            repo_file = os.path.join(os.path.expanduser('~'), f'repositories.offline.thinclient')
            apk_cmd = f"sudo apk --repositories-file {repo_file} --progress add {' '.join(packages)}"
            print(apk_cmd)
            Command('sh')('-c',
                apk_cmd,
                _err_to_out=True, _out=sprint, _in=sys.stdin,
                _out_bufsize=0, _err_bufsize=0,
            )  
        except ErrorReturnCode:
            error = True # error in remote host is already displayed
    finally:
        #pass
        cleanup("thinclient")

def install_packages(host, packages):
    if host == 'thinclient':
        install_in_thinclient(packages)
    elif is_online_host(host):
        install_in_online_host(host, packages)
    else:
        install_in_offline_host(host, packages)
