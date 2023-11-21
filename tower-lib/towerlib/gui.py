from io import StringIO
import os
import uuid
import logging
import time

import sh
from sh import ssh, nxproxy, xsetroot, mcookie

from towerlib.utils.exceptions import NxTimeoutException
from towerlib import sshconf

logger = logging.getLogger('tower')

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
    autodpi="1",
    rootless="1",
)

DEFAULTS_NXPROXY_ARGS = dict(
    retry="5",
    connect="127.0.0.1",
    cleanup="0"
)

NX_TIMEOUT = 5

def ssh_command(hostname, *cmd):
    cmd_uuid = str(uuid.uuid1())
    # protect against data injection via .bashrc files
    ssh_cmd = f'echo SSHBEGIN:{cmd_uuid}; PATH=/usr/local/bin:/usr/bin:/bin sh -c "{" ".join(cmd)}"; echo; echo SSHEND:{cmd_uuid}'
    ssh_res = ssh(hostname, ssh_cmd)
    sanitized_stdout = ""
    is_ssh_data = False
    for line in str(ssh_res).split('\n'):
        if line.startswith(f'SSHBEGIN:{cmd_uuid}'):
            is_ssh_data = True
            continue
        if not is_ssh_data: continue
        if line.startswith(f'SSHEND:{cmd_uuid}'): break
        sanitized_stdout += line + "\n"
    return sanitized_stdout.strip()

def get_real_hostname(hostname):
    return ssh_command(hostname, 'cat /etc/hostname')

def get_home(hostname):
    return ssh_command(hostname, 'echo', '$HOME')

def generate_magic_cookie():
    return mcookie().strip()

def authorize_cookie(hostname, cookie, display_num):
    xauthority_path = os.path.join(get_home(hostname), ".Xauthority")
    ssh(hostname, "touch", xauthority_path)
    ssh(hostname, 'xauth', 
        'add', f"{get_real_hostname(hostname)}/unix:{display_num}", 
        'MIT-MAGIC-COOKIE-1', cookie,
        _out=logger.debug
    )

def get_next_display_num():
    used_nums = []
    for host in sshconf.hosts():
        if not sshconf.is_up(host): continue
        xauth_list = ssh_command(host, 'xauth', 'list')
        if xauth_list == "": continue
        used_nums += [int(line.split(" ")[0].split(":").pop().strip()) for line in xauth_list.split("\n")]
    if len(used_nums) == 0:
        return NXAGENT_FIRST_DISPLAY_NUM
    used_nums.sort()
    return used_nums.pop() + 1
   
def revoke_cookies(hostname, display_num):
    return ssh(hostname, 'xauth', 
        'remove', f"{hostname}/unix:{display_num}", _out=logger.debug
    )

def gen_display_args(display_num, *dicts):
    arg_dicts = list(dicts)
    args = dict(arg_dicts.pop(0))
    for arg_dict in arg_dicts:
        args.update(arg_dict)
    str_args = ",".join([f"{key}={value}" for key, value in args.items()])
    return f"nx/nx,{str_args}:{display_num}"

def wait_for_output(_out, expected_output):
    start_time = time.time()
    elapsed_time = 0
    process_output = ""
    while expected_output not in process_output:
        process_output = _out.getvalue()
        elapsed_time = time.time() - start_time
        if elapsed_time > NX_TIMEOUT:
            logger.info(process_output)
            raise NxTimeoutException("NX agent or proxy not ready after {NX_TIMEOUT}s")
    logger.debug(process_output)

def start_nx_agent(hostname, display_num, cookie, nxagent_args=dict()):
    nxagent_port = NXAGENT_FIRST_PORT + display_num
    display = gen_display_args(
        display_num, DEFAULTS_NXAGENT_ARGS, nxagent_args, 
        {'listen': nxagent_port}
    )
    authorize_cookie(hostname, cookie, display_num)
    buf = StringIO()
    ssh(hostname, 
        '-L', f'{nxagent_port}:127.0.0.1:{nxagent_port}', # ssh tunnel
        f'DISPLAY={display}',
        'LD_LIBRARY_PATH=/usr/lib/nx/X11/',
        'nxagent', '-R', '-nolisten', 'tcp', f':{display_num}',
        _err_to_out=True, _out=buf, _bg=True, _bg_exc=False
    )
    wait_for_output(buf, "Waiting for connection")     
    logger.info("nxagent is waiting for connection...")

def start_nx_proxy(display_num, cookie, nxproxy_args=dict()):
    nxagent_port = NXAGENT_FIRST_PORT + display_num
    display = gen_display_args(
        display_num, DEFAULTS_NXPROXY_ARGS, nxproxy_args,
        {'cookie': cookie, 'port': nxagent_port}
    )
    buf = StringIO()
    nxproxy(
        '-S', display, 
        _err_to_out=True, _out=buf, _bg=True, _bg_exc=False
    )
    #wait_for_output(buf, "Established X server connection") 
    wait_for_output(buf, "Session started")  
    logger.info("nxproxy connected to nxagent.")

def kill_nx_processes(hostname, display_num):
    logger.info(f"closing nxproxy and nxagent ({hostname}:{display_num})..")
    # for alpine 3.17
    killcmd_legacy = f"ps -ef | grep 'nx..... .*:{display_num}' | grep -v grep | awk '{{print $1}}' | xargs kill 2>/dev/null || true"
    killcmd = f"ps -ef | grep 'nx..... .*:{display_num}' | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"
    # nxagent in host
    ssh(hostname, killcmd_legacy)
    ssh(hostname, killcmd)
    # ssh tunnel and nxproxy in thinclient
    sh.Command('sh')('-c', killcmd)

def cleanup(hostname, display_num):
    kill_nx_processes(hostname, display_num)
    revoke_cookies(hostname, display_num)
    xsetroot('-cursor_name', 'left_ptr')

def run(hostname, *cmd):
    app_process = None
    display_num = get_next_display_num()
    try:
        xsetroot('-cursor_name', 'watch')
        cookie = generate_magic_cookie()
        # start nxagent and nxproxy in background
        start_nx_agent(hostname, display_num, cookie)
        start_nx_proxy(display_num, cookie)
        # run the command in foreground
        logger.info(f"run {' '.join(cmd)}")
        app_process = ssh(
            hostname, f"DISPLAY=:{display_num}", *cmd,
            _out=logger.info, _err_to_out=True, _bg=True
        )
        xsetroot('-cursor_name', 'left_ptr')
        app_process.wait()
    except NxTimeoutException:
        logger.error("Failed to initialize NX, please check the log above.")
    finally:
        # kill bakground processes when done
        try:
            if app_process is not None and app_process.is_alive():
                app_process.terminate()
        except:
            pass # we want to cleanup anyway
        cleanup(hostname, display_num)
