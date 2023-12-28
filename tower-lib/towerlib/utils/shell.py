# pylint: disable=import-error,unused-import,no-name-in-module
from sh import (
    Command, ErrorReturnCode, ErrorReturnCode_1,
    cp, rm, mv, ls, cat, tee, echo, mkdir, chown, truncate, sed, touch,
    lsblk, mount, umount, parted, mkdosfs, dd, losetup,
    sync, rsync, tar, xz,
    ssh as sshcli, scp, ssh_keygen, openssl, abuild, abuild_sign, shasum,
    git as gitcli, pip, apk,
    nxproxy, xsetroot, mcookie, waypipe,
    argparse_manpage,
    locale as getlocale,
    doas, runuser,
)
# pylint: enable=import-error,unused-import,no-name-in-module

def ssh(*args, **kwargs):
    return sshcli(*args, **kwargs)

def git(*args, **kwargs):
    return gitcli(*args, **kwargs)
