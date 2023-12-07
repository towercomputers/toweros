# pylint: disable=import-error,unused-import,no-name-in-module
from sh.contrib import sudo as sh_sudo

from sh import (
    Command, ErrorReturnCode,
    cp, rm, mv, ls, cat, tee, echo, mkdir, chown, truncate, sed, touch,
    lsblk, mount, umount, parted, mkdosfs, dd, losetup,
    sync, rsync, tar, xz,
    ssh as sshcli, scp, ssh_keygen, openssl, abuild_sign, shasum,
    git as gitcli, pip, apk, hatch,
    nxproxy, xsetroot, mcookie, waypipe,
    argparse_manpage,
    license_scanner,
    locale as getlocale,
)
# pylint: enable=import-error,unused-import,no-name-in-module

def ssh(*args, **kwargs):
    return sshcli(*args, **kwargs)

def git(*args, **kwargs):
    return gitcli(*args, **kwargs)
