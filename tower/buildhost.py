import os
import time
from datetime import datetime
import logging
import glob

import sh
from sh import (
    Command,
    mount, parted, mkdosfs, resize2fs, tee, cat, echo,
    mv, cp, rm, sync, rsync, chown, truncate, mkdir, ls,
    tar, xz, apk, dd,
    losetup, abuild_sign, openssl
)
mkfs_ext4 = Command('mkfs.ext4')
fsck_ext4 = Command('fsck.ext4')

from tower import utils
from tower.utils import clitask
from tower.__about__ import __version__

logger = logging.getLogger('tower')

WORKING_DIR = os.path.join(os.path.expanduser('~'), 'build-toweros-host-work')
INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'toweros-host')

def wd(path):
    return os.path.join(WORKING_DIR, path)

def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise Exception(f"f{WORKING_DIR} already exists! Is another build in progress? if not, delete this folder and try again.")
    os.makedirs(WORKING_DIR)

def fetch_apk_packages(repo_path, branch, packages):
    apk(
        'fetch', '--arch', 'armv7', '-R', '--url', '--no-cache', '--allow-untrusted',
        '--root', wd("EXPORT_ROOTFS_DIR/boot"),
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{branch}/main',
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{branch}/community',
        '-o', repo_path, *packages, _out=logger.debug
    )

def prepare_apk_repos(private_key_path):
    repo_path = wd("EXPORT_ROOTFS_DIR/boot/apks/armv7/")
    rm('-rf', repo_path)
    mkdir('-p',repo_path)
    world_path = os.path.join(INSTALLER_DIR, 'etc', 'apk', 'world')
    # TODO: remove this and switch to latest-stable on Alpine v3.18 release
    stable_apks, edge_apks = [], []
    for line in cat(world_path, _iter=True):
        package = line.strip()
        if "=" in package:
            edge_apks.append(package.split("=")[0])
        else:
            stable_apks.append(package)
    fetch_apk_packages(repo_path, "latest-stable", stable_apks)
    fetch_apk_packages(repo_path, "edge", edge_apks)
    apks = glob.glob(wd("EXPORT_ROOTFS_DIR/boot/apks/armv7/*.apk"))
    apk_index_path = wd("EXPORT_ROOTFS_DIR/boot/apks/armv7/APKINDEX.tar.gz")
    apk_index_opts = ['index', '--arch', 'armv7', '--rewrite-arch', 'armv7', '--allow-untrusted']
    apk(*apk_index_opts, '-o', apk_index_path, *apks, _out=logger.debug)
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
    mkdir('-p', wd("EXPORT_ROOTFS_DIR"))
    mount(wd("root.img"), wd("EXPORT_ROOTFS_DIR"))
    # put alpine linux files
    mkdir(wd("EXPORT_ROOTFS_DIR/boot"))
    tar('-xpf', alpine_tar_path, '-C', wd("EXPORT_ROOTFS_DIR/boot"))
    prepare_apk_repos(private_key_path)
    # synchronize folder
    sync(wd("EXPORT_ROOTFS_DIR"))

def prepare_overlay(pub_key_path):
    mkdir('-p', wd("overlay/etc/local.d/"))
    cp('-r', os.path.join(INSTALLER_DIR, 'etc'), wd("overlay/"))
    cp(os.path.join(INSTALLER_DIR, 'installer', 'install-host.sh'), wd("overlay/etc/local.d/install-host.start"))
    cp(os.path.join(INSTALLER_DIR, 'installer', 'configure-firewall.sh'), wd("overlay/etc/local.d/configure-firewall.sh"))
    mkdir('-p', wd("overlay/etc/apk/keys/"))
    cp(pub_key_path, wd(f"overlay/etc/apk/keys/{os.path.basename(pub_key_path)}"))
    Command('sh')(
        os.path.join(INSTALLER_DIR, 'genapkovl-toweros-host.sh'),
        wd("overlay"),
        _cwd=wd("EXPORT_ROOTFS_DIR/boot/"),
        _out=print
    )
    cp(wd("EXPORT_ROOTFS_DIR/boot/headless.apkovl.tar.gz"), "/home/tower/")

@clitask("Creating RPI partitions...")
def create_rpi_partitions():
    image_file = wd("toweros-host.img")
    # caluclate sizes
    #cmd = f'du --apparent-size -s {wd("EXPORT_ROOTFS_DIR")} --exclude boot --block-size=1 | cut -f 1'
    #root_size = int(Command('sh')('-c', cmd).strip())
    root_size = 4 * 1024 * 1024 # empty partition
    boot_size = 256 * 1024 * 1024
    # All partition sizes and starts will be aligned to this size
    align = 4 * 1024 * 1024
    # Add this much space to the calculated file size. This allows for
    # some overhead (since actual space usage is usually rounded up to the
    # filesystem block size) and gives some free space on the resulting
    # image.
    root_margin = int(root_size * 0.2 + 200 * 1024 * 1024)
    boot_part_start = align
    boot_part_size = int((boot_size + align - 1) / align) * align
    boot_part_end = boot_part_start + boot_part_size - 1
    root_part_start = boot_part_start + boot_part_size
    root_part_size = int((root_size + root_margin + align  - 1) / align) * align
    root_part_end = root_part_start + root_part_size - 1
    image_size = boot_part_start + boot_part_size + root_part_size
    # create image file
    truncate('-s', image_size, image_file)
    # make partitions
    parted('--script', image_file, 'mklabel', 'msdos', _out=logger.debug)
    parted('--script', image_file, 'unit', 'B', 'mkpart', 'primary', 'fat32', boot_part_start, boot_part_end, _out=logger.debug)
    parted('--script', image_file, 'unit', 'B', 'mkpart', 'primary', 'ext4', root_part_start, root_part_end, _out=logger.debug)

def create_loop_device(image_file):
    loop_dev = losetup('--show', '--find', '--partscan', image_file).strip()
    retry = 1
    while not loop_dev and retry < 5:
        time.sleep(5)
        retry +=1
        loop_dev = losetup('--show', '--find', '--partscan', image_file).strip()
    if loop_dev:
        return loop_dev
    raise Exception("losetup failed; exiting")

@clitask("Copying Alpine Linux system in RPI partitions...")
def prepare_rpi_partitions(loop_dev):
    boot_dev = f"{loop_dev}p1"
    root_dev = f"{loop_dev}p2"
    # format partitions
    mkdosfs('-n', 'bootfs', '-F', 32, '-s', 4, '-v', boot_dev, _out=logger.debug)
    mkfs_ext4('-L', 'rootfs', '-O', "^huge_file", root_dev, _out=logger.debug)
    # mount partitions
    mkdir('-p', wd("ROOTFS_DIR"), _out=logger.debug)
    mount('-v', root_dev, wd("ROOTFS_DIR"), '-t', 'ext4')
    mkdir('-p', wd("ROOTFS_DIR/boot"), _out=logger.debug)
    mount('-v', boot_dev, wd("ROOTFS_DIR/boot"), '-t', 'vfat')
    # copy system in partitions
    rsync('-aHAXxv', '--exclude', '/boot', wd("EXPORT_ROOTFS_DIR/"), wd("ROOTFS_DIR/"), _out=logger.debug)
    rsync('-rtxv', wd("EXPORT_ROOTFS_DIR/boot/"), wd("ROOTFS_DIR/boot/"), _out=logger.debug)

@clitask("Compressing image with xz...")
def compress_image(builds_dir, owner):
    image_path = os.path.join(builds_dir, datetime.now().strftime(f'toweros-host-{__version__}-%Y%m%d%H%M%S.img.xz'))
    xz(
        '--compress', '--force', 
        '--threads', 0, '--memlimit-compress=90%', '--best',
	    '--stdout', wd("toweros-host.img"),
        _out=image_path
    )
    chown(f"{owner}:{owner}", image_path)
    logger.info(f"Image ready: {image_path}")
    return image_path

@clitask("Copying image...")
def copy_image(builds_dir, owner):
    image_path = os.path.join(builds_dir, datetime.now().strftime(f'toweros-host-{__version__}-%Y%m%d%H%M%S.img'))
    cp(wd("toweros-host.img"), image_path)
    chown(f"{owner}:{owner}", image_path)
    logger.info(f"Image ready: {image_path}")
    return image_path

def unmount_all():
    utils.lazy_umount(wd("ROOTFS_DIR/boot/"))
    utils.lazy_umount(wd("ROOTFS_DIR"))
    utils.lazy_umount(wd("EXPORT_ROOTFS_DIR"))
    utils.lazy_umount(wd("BOOTFS_DIR"))
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

@clitask("Building TowserOS-Host image...", timer_message="TowserOS-Host image built in {0}.", sudo=True)
def build_image(builds_dir):
    alpine_tar_path = utils.prepare_required_build("alpine-rpi", builds_dir)
    user = os.getlogin()
    loop_dev = None
    try:
        prepare_working_dir()
        private_key_path, public_key_path = prepare_apk_key()
        prepare_system_image(alpine_tar_path, private_key_path)
        prepare_overlay(public_key_path)
        create_rpi_partitions()
        loop_dev = create_loop_device(wd("toweros-host.img"))
        prepare_rpi_partitions(loop_dev)
        unmount_all()
        image_path = compress_image(builds_dir, user)
        #image_path = copy_image(builds_dir, user)
    finally:
        cleanup()
    return image_path


@clitask("Copying image {0} in device {1}...")
def copy_image_in_device(image_file, device):
    utils.unmount_all(device)
    # burn image
    dd(f'if={image_file}', f'of={device}', 'bs=8M', _out=logger.debug)
    # determine partitions names
    boot_part = Command('sh')('-c', f'ls {device}*1').strip()
    root_part = Command('sh')('-c', f'ls {device}*2').strip()
    if not boot_part or not root_part:
        raise Exception("Invalid partitions")
    # extend root partition
    parted(device, 'resizepart', 2, '100%')
    resize2fs(root_part)
    return boot_part, root_part

@clitask("Configuring image...")
def insert_tower_env(boot_part, config):
    mkdir('-p', wd("BOOTFS_DIR/"))
    mount(boot_part, wd("BOOTFS_DIR/"), '-t', 'vfat')
    str_env = "\n".join([f"{key}='{value}'" for key, value in config.items()])
    logger.info(f"Host configuration:\n{str_env}")
    tee(wd("BOOTFS_DIR/tower.env"), _in=echo(str_env))
    #ls('-al', wd("BOOTFS_DIR/"), _out=print)
    

@clitask("Installing TowserOS-Host in {1}...", timer_message="TowserOS-Host installed in {0}.", sudo=True)
def burn_image(image_file, device, config):
    try:
        prepare_working_dir()
        boot_part, root_part = copy_image_in_device(image_file, device)
        insert_tower_env(boot_part, config)       
    finally:
        cleanup()
