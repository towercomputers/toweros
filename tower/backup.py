import os
import logging
from io import StringIO

from sh import ssh, restic, ErrorReturnCode

from tower import sshconf
from tower.utils import clitask

logger = logging.getLogger('tower')

HOME_PATH = os.path.expanduser('~')

def init_host_restic_repo(host, password):
    buf = StringIO()
    if sshconf.is_up(host):
        try:
            ssh(
                host, 
                f'RESTIC_PASSWORD={password}', 
                'restic', 'init', '--repo', f'/home/{sshconf.DEFAULT_SSH_USER}/backup',
                _out=buf, _err=buf
            )
        except ErrorReturnCode as e:
            out = buf.getvalue()
            if 'config file already exists' in out:
                pass
            else:
                logger.error(buf.getvalue())
                raise e
    else:
        raise Exception(f'Host {host} is not up')

def init_thinclient_restic_repo(password):
    buf = StringIO()
    try:
        restic('init', '--repo', f'{HOME_PATH}/backup', _out=buf, _err=buf, _env={'RESTIC_PASSWORD': password})
    except ErrorReturnCode as e:
        out = buf.getvalue()
        if 'config file already exists' in out:
            pass
        else:
            logger.error(buf.getvalue())
            raise e

@clitask('Backup host {0}...')
def backup_host(host, password):
    init_host_restic_repo(host, password)
    ssh(
        host, 
        f'RESTIC_PASSWORD={password}', 
        'restic', 
        '--repo', f'/home/{sshconf.DEFAULT_SSH_USER}/backup', 
        'backup', f'/home/{sshconf.DEFAULT_SSH_USER}/',
        '--exclude', f'/home/{sshconf.DEFAULT_SSH_USER}/backup'
    )
    restic(
        '--repo', f'{HOME_PATH}/backup',
        'copy',
        '--from-repo', f'sftp:{host}:/home/{sshconf.DEFAULT_SSH_USER}/backup',
        'latest',
        _env=dict(os.environ) | {'RESTIC_PASSWORD': password, 'RESTIC_FROM_PASSWORD': password}
    )

@clitask('Backup thinclient...')
def backup_thinclient(password):
    init_thinclient_restic_repo(password)
    restic(
        '--repo', f'{HOME_PATH}/backup', 
        'backup', HOME_PATH,
        '--exclude', f'{HOME_PATH}/backup',
        _env={'RESTIC_PASSWORD': password}
    )

@clitask("Backup thinclient an all hosts...", task_parent=True)
def backup_all(password, cold_device=None):
    backup_thinclient(password)
    for host in sshconf.hosts():
        backup_host(host, password)
