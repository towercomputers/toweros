#!/usr/bin/env python3

# usage: ./nxssh.py <hostname> <cmd>
# example: ./nxssh.py office galculator

from io import StringIO
import os
import random
import uuid
import logging
import sys
import time

import sh
from sh import ssh, nxproxy, xinit

logger = logging.getLogger('tower') # TODO

NXAGENT_FIRST_PORT = 4000
NXAGENT_FIRST_DISPLAY_NUM = 50

DEFAULTS_NXAGENT_ARGS=dict(
    link="lan",
    limit="0",
    cache="8M",
    images="32M",
    accept="127.0.0.1",
    clipboard="both",
    client="linux",
    menu="0",
    keyboard="clone",
    composite="1",
    autodpi="1"
)

DEFAULTS_NXPROXY_ARGS = dict(
    retry="5",
    connect="127.0.0.1",
    cleanup="0"
)

NX_TIMEOUT = 5

class NxTimeoutException(Exception):
    pass

def ssh_command(hostname, *cmd):
    cmd_uuid = str(uuid.uuid1())
    # protect against data injection via .bashrc files
    ssh_cmd = f'echo SSHBEGIN:{cmd_uuid}; PATH=/usr/local/bin:/usr/bin:/bin sh -c "{" ".join(cmd)}"; echo; echo SSHEND:{cmd_uuid}'
    buf = StringIO()
    ssh(hostname, ssh_cmd, _out=buf)
    sanitized_stdout = ""
    is_ssh_data = False
    for line in buf.getvalue().split('\n'):
        if line.startswith(f'SSHBEGIN:{cmd_uuid}'):
            is_ssh_data = True
            continue
        if not is_ssh_data: continue
        if line.startswith(f'SSHEND:{cmd_uuid}'): break
        sanitized_stdout += line + "\n"
    return sanitized_stdout.strip()

def get_real_hostname(hostname):
    return ssh_command(hostname, 'hostname')

def get_home(hostname):
    return ssh_command(hostname, 'echo', '$HOME')

def generate_magic_cookie():
    return hex(random.getrandbits(128))[2:]

def authorize_cookie(hostname, cookie, display_num):
    xauthority_path = os.path.join(get_home(hostname), ".Xauthority")
    ssh(hostname, "touch", xauthority_path)
    ssh(hostname, 'xauth', 
        'add', f"{get_real_hostname(hostname)}/unix:{display_num}", 
        'MIT-MAGIC-COOKIE-1', cookie
    )
   
def revoke_cookies(hostname, display_num):
    return ssh(hostname, 'xauth', 
        'remove', f":{display_num}", _out=print
    )

def start_nx_agent(hostname, display_num, cookie, nxagent_args=dict()):
    nxagent_port = NXAGENT_FIRST_PORT + display_num
    args = dict(DEFAULTS_NXAGENT_ARGS)
    args.update(nxagent_args)
    args.update({'listen': nxagent_port})
    str_args = ",".join([f"{key}={value}" for key, value in args.items()])
    display = f"nx/nx,{str_args}:{display_num}"
    authorize_cookie(hostname, cookie, display_num)
    buf = StringIO()
    nxagent_process = ssh(hostname, 
        '-L', f'{nxagent_port}:127.0.0.1:{nxagent_port}',
        f'DISPLAY={display}',
        'nxagent', '-R', '-nolisten', 'tcp', f':{display_num}',
        _err_to_out=True, _out=buf, _bg=True, _bg_exc=False
    )
    start_time = time.time()
    elapsed_time = 0
    nxagent_output = ""
    while "Waiting for connection" not in nxagent_output:
        nxagent_output = buf.getvalue()
        elapsed_time = time.time() - start_time
        if elapsed_time > NX_TIMEOUT:
            print(nxagent_output)
            raise NxTimeoutException("nxagent not ready after {NX_TIMEOUT}s")
        
    print("nxagent is waiting for connection...")
    return nxagent_process

def kill_nx_agent(hostname, display_num):
    kill_command = f"ps -ef | grep 'nxagent .*:{display_num}' | grep -v grep | awk '{{print $2}}' | xargs kill"
    try:
        ssh(hostname, kill_command)
    except sh.ErrorReturnCode:
        pass # fail silently if no process to kill
    try:
        sh.Command('sh')('-c', kill_command)
    except sh.ErrorReturnCode:
        pass # fail silently if no process to kill

def kill_nx_proxy(display_num):
    try:
        kill_command = f"ps -ef | grep 'nxproxy .*:{display_num}' | grep -v grep | awk '{{print $2}}' | xargs kill"
        sh.Command('sh')('-c', kill_command)
    except sh.ErrorReturnCode:
        pass # fail silently if no process to kill

def start_nx_proxy(display_num, cookie, nxproxy_args=dict()):
    nxagent_port = NXAGENT_FIRST_PORT + display_num
    args = dict(DEFAULTS_NXPROXY_ARGS)
    args.update(nxproxy_args)
    args.update({'cookie': cookie, 'port': nxagent_port})
    str_args = ",".join([f"{key}={value}" for key, value in args.items()])
    display = f"nx/nx,{str_args}:{display_num}"
    buf = StringIO()
    nxproxy_process = nxproxy(
        '-S', display, 
        _err_to_out=True, _out=buf, _bg=True, _bg_exc=False
    )
    start_time = time.time()
    elapsed_time = 0
    nxproxy_output = ""
    while "Established X server connection" not in nxproxy_output:
        nxproxy_output = buf.getvalue()
        elapsed_time = time.time() - start_time
        if elapsed_time > NX_TIMEOUT:
            print(nxproxy_output)
            raise NxTimeoutException("nxproxy not ready after {NX_TIMEOUT}s")

    print("nxproxy connected to nxagent.")
    return nxproxy_process

def get_next_display_num(hostname):
    xauth_list = ssh_command(hostname, 'xauth', 'list')
    if xauth_list == "":
        return NXAGENT_FIRST_DISPLAY_NUM
    used_num = [int(line.split(" ")[0].split(":").pop().strip()) for line in xauth_list.split("\n")]
    used_num.sort()
    return used_num.pop() + 1

def cleanup(hostname, display_num):
    print("closing nxproxy and nxagent..")
    kill_nx_proxy(display_num)
    kill_nx_agent(hostname, display_num)
    revoke_cookies(hostname, display_num)

def run_nx_command(hostname, *cmd):
    app_process = None
    try:
        display_num = get_next_display_num(hostname)
        cookie = generate_magic_cookie()
        # start nxagent and nxproxy in background
        start_nx_agent(hostname, display_num, cookie)
        start_nx_proxy(display_num, cookie)
        # run the command in foreground
        print(f"run {' '.join(cmd)}")
        app_process = ssh(hostname, f"DISPLAY=:{display_num}", *cmd)
    except NxTimeoutException:
        print("Failed to initialize NX, please check the log above.")
    except KeyboardInterrupt:
        if app_process and app_process.is_alive():
            app_process.terminate()
    finally:
        # kill bakground processes when done
        cleanup(hostname, display_num)
        

# TODO
def main():
    args = sys.argv
    hostname = sys.argv[1]
    cmd = sys.argv[2:]
    if os.getenv('DISPLAY'):
        run_nx_command(hostname, *cmd)
    else:
        cmd = " ".join(['xinit'] + sys.argv + ['--', ':0', 'vt1'])
        os.system(cmd)

if __name__ == '__main__':
    main()