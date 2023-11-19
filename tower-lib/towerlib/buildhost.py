import os
import time
from datetime import datetime
import logging
import glob
import getpass
from io import StringIO

import sh
from sh import (
    Command, ErrorReturnCode,
    mount, parted, mkdosfs, tee, cat, echo,
    cp, rm, sync, rsync, chown, truncate, mkdir,
    tar, xz, apk, dd,
    losetup, abuild_sign, openssl,
)
mkfs_ext4 = Command('mkfs.ext4')
fsck_ext4 = Command('fsck.ext4')

from towerlib import utils
from towerlib.utils import clitask
from towerlib.__about__ import __version__
from towerlib.sshconf import TOWER_NETWORK_ONLINE, TOWER_NETWORK_OFFLINE, TOWER_DIR
from towerlib.utils.exceptions import LockException, BuildException

logger = logging.getLogger('tower')

WORKING_DIR = os.path.join(os.path.expanduser('~'), 'build-toweros-host-work')
INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'toweros-installers', 'toweros-host')

ALPINE_BRANCH_FOR_UNVERSIONED = "v3.17"
ALPINE_BRANCH_FOR_VERSIONED = "v3.18"
USERNAME = getpass.getuser()

sprint = lambda str: print(str, end='', flush=True)

def wd(path):
    return os.path.join(WORKING_DIR, path)

def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise LockException(f"f{WORKING_DIR} already exists! Is another build in progress? if not, delete this folder and try again.")
    os.makedirs(WORKING_DIR)

def fetch_apk_packages(repo_path, branch, packages):
    apk(
        'fetch', '--arch', 'armv7', '-R', '--url', '--no-cache', '--allow-untrusted',
        '--root', wd("EXPORT_BOOTFS_DIR"),
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{branch}/main',
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{branch}/community',
        '-o', repo_path, *packages, _out=logger.debug
    )

def prepare_apk_repos(private_key_path):
    repo_path = wd("EXPORT_BOOTFS_DIR/apks/armv7/")
    rm('-rf', repo_path)
    mkdir('-p',repo_path)
    world_path = os.path.join(INSTALLER_DIR, 'etc', 'apk', 'world')
    # TODO: test and remove this on Alpine v3.19 release
    unversioned_apks, versioned_apks = [], []
    for line in cat(world_path, _iter=True):
        package = line.strip()
        if package == "linux-firmware-brcm-cm4":
            continue
        if "=" in package:
            versioned_apks.append(package.split("=")[0])
        else:
            unversioned_apks.append(package)
    # download packages
    fetch_apk_packages(repo_path, ALPINE_BRANCH_FOR_UNVERSIONED, unversioned_apks)
    fetch_apk_packages(repo_path, ALPINE_BRANCH_FOR_VERSIONED, versioned_apks)
    # build and copy linux-firmware-brcm-cm4
    Command('sh')(
        '-c',
        f'runuser -u {USERNAME} -- abuild -r',
        _cwd=os.path.join(INSTALLER_DIR, 'linux-firmware-brcm-cm4')
    )
    cp("/home/tower/packages/toweros-host/x86_64/linux-firmware-brcm-cm4-1.0-r0.apk", repo_path)
    # prepare index
    apks = glob.glob(wd("EXPORT_BOOTFS_DIR/apks/armv7/*.apk"))
    apk_index_path = wd("EXPORT_BOOTFS_DIR/apks/armv7/APKINDEX.tar.gz")
    apk_index_opts = ['index', '--arch', 'armv7', '--rewrite-arch', 'armv7', '--allow-untrusted']
    apk(*apk_index_opts, '-o', apk_index_path, *apks, _out=logger.debug)
    # sign index
    abuild_sign('-k', private_key_path, apk_index_path, _out=logger.debug)

@clitask("Preparing Alpine Linux system...")
def prepare_system_image(alpine_tar_path, private_key_path):
    # prepare disk image
    mkfs_ext4(
        '-O', '^has_journal,^resize_inode', 
        '-E', 'lazy_itable_init=0,root_owner=0:0',
        '-m', '0',
        '-U', 'clear',
        '--', wd("root.img"), '4G',
        _out=logger.debug
    )
    # mount image in temporary folder
    mkdir('-p', wd("EXPORT_BOOTFS_DIR"))
    mount(wd("root.img"), wd("EXPORT_BOOTFS_DIR"))
    # put alpine linux files
    tar('-xpf', alpine_tar_path, '-C', wd("EXPORT_BOOTFS_DIR"))
    prepare_apk_repos(private_key_path)
    # synchronize folder
    sync(wd("EXPORT_BOOTFS_DIR"))

def prepare_overlay(pub_key_path):
    # put installer in local.d
    mkdir('-p', wd("overlay/etc/local.d/"))
    cp('-r', os.path.join(INSTALLER_DIR, 'etc'), wd("overlay/"))
    cp(os.path.join(INSTALLER_DIR, 'installer', 'install-host.sh'), wd("overlay/etc/local.d/install-host.start"))
    cp(os.path.join(INSTALLER_DIR, 'installer', 'configure-firewall.sh'), wd("overlay/etc/local.d/configure-firewall.sh"))
    # put public key used to signe apk index
    mkdir('-p', wd("overlay/etc/apk/keys/"))
    cp(pub_key_path, wd(f"overlay/etc/apk/keys/{os.path.basename(pub_key_path)}"))
    # generate the overlay in the boot folder
    Command('sh')(
        os.path.join(INSTALLER_DIR, 'genapkovl-toweros-host.sh'),
        wd("overlay"),
        _cwd=wd("EXPORT_BOOTFS_DIR/"),
        _out=print
    )
    tee(wd("EXPORT_BOOTFS_DIR/usercfg.txt"), _in=echo("dtoverlay=dwc2,dr_mode=host"))

@clitask("Creating RPI partitions...")
def create_rpi_boot_partition():
    image_file = wd("toweros-host.img")
    # caluclate sizes
    boot_size = 256 * 1024 * 1024
    # All partition sizes and starts will be aligned to this size
    align = 4 * 1024 * 1024
    # Add this much space to the calculated file size. This allows for
    # some overhead (since actual space usage is usually rounded up to the
    # filesystem block size) and gives some free space on the resulting
    # image.
    boot_part_start = align
    boot_part_size = int((boot_size + align - 1) / align) * align
    boot_part_end = boot_part_start + boot_part_size - 1
    image_size = boot_part_start + boot_part_size
    # create image file
    truncate('-s', image_size, image_file)
    # make partitions
    parted('--script', image_file, 'mklabel', 'msdos', _out=logger.debug)
    parted('--script', image_file, 'unit', 'B', 'mkpart', 'primary', 'fat32', boot_part_start, boot_part_end, _out=logger.debug)

def create_loop_device(image_file):
    loop_dev = losetup('--show', '--find', '--partscan', image_file).strip()
    retry = 1
    while not loop_dev and retry < 5:
        time.sleep(5)
        retry +=1
        loop_dev = losetup('--show', '--find', '--partscan', image_file).strip()
    if loop_dev:
        return loop_dev
    raise BuildException("losetup failed; exiting")

@clitask("Copying Alpine Linux system in RPI partitions...")
def prepare_rpi_partitions(loop_dev):
    boot_dev = f"{loop_dev}p1"
    # format partitions
    mkdosfs('-n', 'bootfs', '-F', 32, '-s', 4, '-v', boot_dev, _out=logger.debug)
    # mount partitions
    mkdir('-p', wd("BOOTFS_DIR"), _out=logger.debug)
    mount('-v', boot_dev, wd("BOOTFS_DIR"), '-t', 'vfat')
    # copy system in partitions
    rsync('-rtxv', wd("EXPORT_BOOTFS_DIR/"), wd("BOOTFS_DIR/"), _out=logger.debug)

@clitask("Compressing image with xz...")
def compress_image(builds_dir):
    image_name = datetime.now().strftime(f'toweros-host-{__version__}-%Y%m%d%H%M%S.img.xz')
    tmp_image_path = os.path.join("/tmp", image_name)
    image_path = os.path.join(builds_dir, image_name)
    xz(
        '--compress', '--force', 
        '--threads', 0, '--memlimit-compress=90%', '--best',
	    '--stdout', wd("toweros-host.img"),
        _out=tmp_image_path
    )
    cp(tmp_image_path, image_path)
    chown(f"{USERNAME}:{USERNAME}", image_path)
    return image_path

@clitask("Copying image...")
def copy_image(builds_dir):
    image_path = os.path.join(builds_dir, datetime.now().strftime(f'toweros-host-{__version__}-%Y%m%d%H%M%S.img'))
    cp(wd("toweros-host.img"), image_path)
    chown(f"{USERNAME}:{USERNAME}", image_path)
    return image_path

def unmount_all():
    utils.lazy_umount(wd("BOOTFS_DIR"))
    utils.lazy_umount(wd("EXPORT_BOOTFS_DIR"))
    losetup('-D')

@clitask("Cleaning up...")
def cleanup():
    unmount_all()
    rm('-rf', WORKING_DIR, _out=logger.debug)

def prepare_apk_key():
    mkdir('-p', wd("apk-keys"))
    private_key_path = wd("apk-keys/tower.rsa")
    public_key_path = wd("apk-keys/tower.rsa.pub")
    openssl('genrsa', '-out', private_key_path, '2048')
    openssl('rsa', '-in', private_key_path, '-pubout', '-out', public_key_path)
    return private_key_path, public_key_path

@clitask("Building TowerOS-Host image...", timer_message="TowserOS-Host image built in {0}.", sudo=True, task_parent=True)
def build_image(builds_dir, uncompressed=False):
    alpine_tar_path = utils.prepare_required_build("alpine-rpi", builds_dir)
    loop_dev = None
    image_path = None
    try:
        prepare_working_dir()
        private_key_path, public_key_path = prepare_apk_key()
        prepare_system_image(alpine_tar_path, private_key_path)
        prepare_overlay(public_key_path)
        create_rpi_boot_partition()
        loop_dev = create_loop_device(wd("toweros-host.img"))
        prepare_rpi_partitions(loop_dev)
        unmount_all()
        if uncompressed:
            image_path = copy_image(builds_dir)
        else:
            image_path = compress_image(builds_dir)
    finally:
        cleanup()
    if image_path:
        logger.info(f"Image ready: {image_path}")
    return image_path

@clitask("Copying {0} in {1}...")
def copy_image_in_device(image_file, device):
    utils.unmount_all(device)
    # burn image
    try:
        buf = StringIO()
        dd(f'if={image_file}', f'of={device}', 'bs=8M', _out=buf)
    except ErrorReturnCode:
        error_message = "Error copying image, please check the boot device integrity or try again with the flag `--zero-device`."
        logger.error(buf.getvalue())
        logger.error(error_message)
        raise BuildException(error_message)
    # determine partition name
    boot_part = Command('sh')('-c', f'ls {device}*1').strip()
    if not boot_part:
        raise BuildException("Invalid partitions")
    return boot_part

@clitask("Zeroing {0} please be patient...")
def zeroing_device(device):
    dd('if=/dev/zero', f'of={device}', 'bs=8M', _out=logger.debug)

@clitask("Configuring image...")
def insert_tower_env(boot_part, config):
    # mount boot partition
    mkdir('-p', wd("BOOTFS_DIR/"))
    mount(boot_part, wd("BOOTFS_DIR/"), '-t', 'vfat')
    str_env = "\n".join([f"{key}='{value}'" for key, value in config.items()])
    logger.debug(f"Host configuration:\n{str_env}")
    # insert tower.env file in boot partition
    tee(wd("BOOTFS_DIR/tower.env"), _in=echo(str_env))
    # insert luks key in boot partition
    keys_path = os.path.join(TOWER_DIR, 'hosts', config['HOSTNAME'], "crypto_keyfile.bin")
    cp(keys_path, wd("BOOTFS_DIR/crypto_keyfile.bin"))

@clitask("Installing TowserOS-Host in {1}...", timer_message="TowserOS-Host installed in {0}.", sudo=True, task_parent=True)
def burn_image(image_file, device, config, zero_device=False):
    try:
        # make sur the password is not shown in logs
        del(config['PASSWORD'])
        prepare_working_dir()
        if zero_device:
            zeroing_device(device)
        boot_part = copy_image_in_device(image_file, device)
        insert_tower_env(boot_part, config)
    finally:
        cleanup()
