import os
import logging
import sys
from urllib.parse import urlparse

from sh import ssh, scp, rm, Command, ErrorReturnCode

from tower.utils import clitask

logger = logging.getLogger('tower')

FIRST_FREE_PORT = 4666

PACMAN_REPOS_URL = {
    'armv7h': "https://ftp.halifax.rwth-aachen.de/archlinux-arm/armv7h/{0}",
    'x86_64': "https://ftp.halifax.rwth-aachen.de/archlinux/{0}/os/x86_64/"
}
REPOS = {
    'armv7h': ['core', 'extra', 'community', 'aur', 'alarm'],
    'x86_64': ['core', 'extra', 'community'],
}
LOCAL_TUNNELING_PORT = 4666

def prepare_pacman_conf(host, arch="armv7h"):
    file_name = os.path.join(os.path.expanduser('~'), f'pacman.offline.{host}.conf')
    # use temporary pacman conf as lock file
    if os.path.exists(file_name):
        raise Exception(f"f{file_name} already exists! Is another install in progress? if not, delete this file and try again.")
    # generate temporary pacman conf 
    with open(file_name, 'w') as fp:
        for repo in REPOS[arch]:
            fp.write(f"[{repo}]\n")
            fp.write("SigLevel = PackageRequired\n")
            fp.write(f"Server = {PACMAN_REPOS_URL[arch].format(repo)}\n")
    # copy pacman conf in offline host
    scp(file_name, f"{host}:~/")

@clitask("Preparing installation...")
def prepare_offline_host(host, arch="armv7h"):
    # prepare pacman conf in offline host
    prepare_pacman_conf(host, arch)
    # add repo host in /etc/hosts
    repo_host = urlparse(PACMAN_REPOS_URL[arch]).netloc
    ssh(host, f"echo '127.0.0.1 {repo_host}' | sudo tee -a /etc/hosts")
    # add iptables rule to redirect https requests to port 4443
    ssh(host, "sudo iptables -t nat -A OUTPUT -p tcp -m tcp --dport 443 -j REDIRECT --to-ports 4443")

def cleanup_offline_host(host, arch="armv7h"):
    # remove temporary pacman conf
    file_name = os.path.join(os.path.expanduser('~'), f'pacman.offline.{host}.conf')
    rm('-f', file_name)
    ssh(host, f"rm -f ~/pacman.offline.{host}.conf")
    # clean /etc/hosts
    repo_host = urlparse(PACMAN_REPOS_URL[arch]).netloc
    ssh(host, f"sudo sed -i '/{repo_host}/d' /etc/hosts")
    # clean iptables
    #ssh(host, "sudo iptables -t nat -D OUTPUT $(sudo iptables -nvL -t nat --line-numbers | grep -m 1 '443 redir ports 4443' | awk '{print $1}')")
    ssh(host, "sudo iptables -t nat -F")

def kill_ssh(arch="armv7h"):
    repo_host = urlparse(PACMAN_REPOS_URL[arch]).netloc
    killcmd = f"ps -ef | grep '{LOCAL_TUNNELING_PORT}:{repo_host}:443' | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"
    Command('sh')('-c', killcmd)

def cleanup(host, arch="armv7h"):
    logger.info("Cleaning up...")
    kill_ssh(arch)
    cleanup_offline_host(host, arch)

sprint = lambda str: print(str, end='', flush=True)

@clitask("Installing {2} in {0}...")
def install_in_offline_host(host, online_host, packages):
    try:
        # prepare offline host
        prepare_offline_host(host)
        # run ssh tunnel with online host in background
        repo_host = urlparse(PACMAN_REPOS_URL["armv7h"]).netloc
        ssh(
            '-L', f"{LOCAL_TUNNELING_PORT}:{repo_host}:443", '-N', '-v',
            online_host,
            _err_to_out=True, _out=logger.debug, _bg=True, _bg_exc=False
        )
        # run pacman in offline host
        logger.info(f"Running pacman in {host}...")
        try:
            ssh(
                '-R', f'4443:127.0.0.1:{LOCAL_TUNNELING_PORT}', '-t',
                host,
                f"sudo pacman --config ~/pacman.offline.{host}.conf -Suy {' '.join(packages)}",
                _err=sprint, _out=sprint, _in=sys.stdin,
                _out_bufsize=0, _err_bufsize=0,
            )
            logger.info("Package(s) installed.")
        except ErrorReturnCode:
            pass # error in remote host is already displayed
    finally:
        cleanup(host, "armv7h")


@clitask("Installing {1} in {0}...", timer_message="Package(s) installed in {0}.")
def install_in_online_host(host, packages):
    # we just need to run pacman with ssh...
    try:
        ssh(
            '-t', host,
            f"sudo pacman -Suy {' '.join(packages)}",
            _err=sprint, _out=sprint, _in=sys.stdin,
            _out_bufsize=0, _err_bufsize=0,
        )
    except ErrorReturnCode:
        pass # error in remote host is already displayed
