import os
import time
from datetime import datetime, timedelta
import logging
import math
import glob

import sh
from sh import (
    Command, ErrorReturnCode,
    mount, umount, parted, mkdosfs,
    cp, rm, sync, rsync, chown, truncate, mkdir, ls, dd, genfstab, resize2fs,
    arch_chroot, 
    bsdtar, xz,
    losetup, 
)
mkfs_ext4 = Command('mkfs.ext4')
fsck_ext4 = Command('fsck.ext4')

from tower import utils
from tower.utils import clitask

logger = logging.getLogger('tower')

ARCHLINUX_ARM_URL = "http://os.archlinuxarm.org/os/ArchLinuxARM-rpi-armv7-latest.tar.gz"
WORKING_DIR = os.path.join(os.getcwd(), 'build-towerospi-work')
INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'towerospi')

def wd(path):
    return os.path.join(WORKING_DIR, path)

def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise Exception(f"f{WORKING_DIR} already exists! Is another build in progress? if not, delete this folder and try again.")
    os.makedirs(WORKING_DIR)

def find_archlinux_arm(builds_dir):
    archlinux_tar_path = os.path.join(builds_dir, 'ArchLinuxARM-rpi-armv7-latest.tar.gz')
    if not os.path.isfile(archlinux_tar_path):
        logger.info("Arch Linux tar not found in builds directory.")
        utils.download_file(ARCHLINUX_ARM_URL, archlinux_tar_path)
    return archlinux_tar_path

def find_nx_build(builds_dir):
    nx_tar_path = os.path.join(builds_dir, 'nx-armv7h.tar.gz')
    if not os.path.isfile(nx_tar_path):
        # TODO: build after user confirmation or/and download from trused repo
        raise Exception("NX build not found")
    return nx_tar_path

@clitask("Preparing Arch Linux system...")
def prepare_chroot_image(archlinux_tar_path, nx_tar_path):
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
    mount('--mkdir', wd("root.img"), wd("EXPORT_ROOTFS_DIR"), _out=logger.debug)
    # put arch linux files
    bsdtar('-xpf', archlinux_tar_path, '-C', wd("EXPORT_ROOTFS_DIR"), _out=logger.debug)
    # put nx packages
    bsdtar('-xpf', nx_tar_path, '-C', wd("EXPORT_ROOTFS_DIR"), _out=logger.debug)
    # put cross platform emulator
    cp('/usr/bin/qemu-arm-static', wd("EXPORT_ROOTFS_DIR/usr/bin"))
    # put and run towerospi installer
    cp(f'{INSTALLER_DIR}/00_install_towerospi.sh', wd("EXPORT_ROOTFS_DIR"))
    arch_chroot(wd("EXPORT_ROOTFS_DIR"), 'sh', '/00_install_towerospi.sh', _out=logger.debug)
    # clean installation files
    rm(wd("EXPORT_ROOTFS_DIR/00_install_towerospi.sh"))
    rm(wd("EXPORT_ROOTFS_DIR/usr/bin/qemu-arm-static"))
    nx_tar_name = os.path.basename(nx_tar_path).split(".")[0]
    rm('-rf', wd(f"EXPORT_ROOTFS_DIR/{nx_tar_name}"))
    # synchronize folder
    sync(wd("EXPORT_ROOTFS_DIR"))

@clitask("Creating RPI partitions...")
def create_rpi_partitions():
    image_file = wd("toweros-pi.img")
    # caluclate sizes
    cmd = f'du --apparent-size -s {wd("EXPORT_ROOTFS_DIR")} --exclude boot --block-size=1 | cut -f 1'
    root_size = int(Command('sh')('-c', cmd).strip())
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

@clitask("Copying Arch Linux system in RPI partitions...")
def prepare_rpi_partitions(loop_dev):
    boot_dev = f"{loop_dev}p1"
    root_dev = f"{loop_dev}p2"
    # format partitions
    mkdosfs('-n', 'bootfs', '-F', 32, '-s', 4, '-v', boot_dev, _out=logger.debug)
    mkfs_ext4('-L', 'rootfs', '-O', "^huge_file", root_dev, _out=logger.debug)
    # mount partitions
    mount('--mkdir', '-v', root_dev, wd("ROOTFS_DIR"), '-t', 'ext4')
    mount('--mkdir', '-v', boot_dev, wd("ROOTFS_DIR/boot"), '-t', 'vfat')
    # copy system in partitions
    rsync('-aHAXxv', '--exclude', '/boot', wd("EXPORT_ROOTFS_DIR/"), wd("ROOTFS_DIR/"), _out=logger.debug)
    rsync('-rtxv', wd("EXPORT_ROOTFS_DIR/boot/"), wd("ROOTFS_DIR/boot/"), _out=logger.debug)

@clitask("Compressing image with xz...")
def compress_image(builds_dir, owner):
    image_path = os.path.join(builds_dir, datetime.now().strftime('towerospi-%Y%m%d%H%M%S.img.xz'))
    xz(
        '--compress', '--force', 
        '--threads', 0, '--memlimit-compress=90%', '--best',
	    '--stdout', wd("toweros-pi.img"),
        _out=image_path
    )
    chown(f"{owner}:{owner}", image_path)
    logger.info(f"Image ready: {image_path}")
    return image_path

def unmount_all():
    utils.lazy_umount(wd("ROOTFS_DIR/boot/"))
    utils.lazy_umount(wd("ROOTFS_DIR"))
    utils.lazy_umount(wd("EXPORT_ROOTFS_DIR"))
    losetup('-D')

@clitask("Cleaning up...")
def cleanup():
    unmount_all()
    rm('-rf', WORKING_DIR, _out=logger.debug)

@clitask("Building TowserOS PI image...", timer_message="TowserOS PI image built in {0}.", sudo=True)
def build_image(builds_dir):
    archlinux_tar_path = find_archlinux_arm(builds_dir)
    nx_tar_path = find_nx_build(builds_dir)
    user = os.getlogin()
    try:
        prepare_working_dir()
        prepare_chroot_image(archlinux_tar_path, nx_tar_path)
        create_rpi_partitions()
        loop_dev = create_loop_device(wd("toweros-pi.img"))
        prepare_rpi_partitions(loop_dev)
        unmount_all()
        image_path = compress_image(builds_dir, user)
    finally:
        cleanup()
    return image_path

@clitask("Copying image {0} in device {1}")
def copy_image(image_file, device):
    utils.unmount_all(device)
    dd(f"if={image_file}", f"of={device}", "bs=8M", "conv=sync", "status=progress", _out=logger.debug)
    boot_part = Command('sh')('-c', f'ls {device}*1').strip()
    root_part = Command('sh')('-c', f'ls {device}*2').strip()
    if not boot_part or not root_part:
        raise Exception("Invalid partitions")
    # extend root partition
    parted(device, 'resizepart', 2, '100%')
    resize2fs(root_part)
    return boot_part, root_part

@clitask("Configuring image with {0}")
def configure_image(config):
    # put cross platform emulator
    cp('/usr/bin/qemu-arm-static', wd("ROOTFS_DIR/usr/bin"))
    # put configuration scripts
    cp(f'{INSTALLER_DIR}/01_configure_towerospi.sh', wd("ROOTFS_DIR/root/"))
    cp(f'{INSTALLER_DIR}/files/towerospi_iptables.rules', wd("ROOTFS_DIR/root/"))
    # run configuration script
    args_key = [
        "HOSTNAME", "USERNAME", "PUBLIC_KEY", "ENCRYPTED_PASSWORD",
        "KEYMAP", "TIMEZONE", "LANG",
        "ONLINE", "WLAN_SSID", "WLAN_SHARED_KEY",
        "THIN_CLIENT_IP", "TOWER_NETWORK"
    ]
    args = [config[key] for key in args_key]
    arch_chroot(wd("ROOTFS_DIR"), 'sh', '/root/01_configure_towerospi.sh', *args, _out=logger.debug, _err_to_out=True)
    # update fstab
    #tee(wd("ROOTFS_DIR/etc/fstab"), _in=genfstab('-U', wd("ROOTFS_DIR")))
    Command('sh')('-c', f'genfstab -U {wd("ROOTFS_DIR")} | sed "/swap/d" | sed "/#/d" > {wd("ROOTFS_DIR/etc/fstab")}')
    # clean configuration files
    rm(wd("ROOTFS_DIR/root/01_configure_towerospi.sh"))
    rm(wd("ROOTFS_DIR/root/towerospi_iptables.rules"))
    rm(wd("ROOTFS_DIR/usr/bin/qemu-arm-static")) 

@clitask("Installing TowserOS PI in {1}...", timer_message="TowserOS PI installed in {0}.", sudo=True)
def burn_image(image_file, device, config):
    try:
        prepare_working_dir()
        boot_part, root_part = copy_image(image_file, device)
        # mount partions
        mount('--mkdir', root_part, wd("ROOTFS_DIR"), '-t', 'ext4')
        mount('--mkdir', boot_part, wd("ROOTFS_DIR/boot/"), '-t', 'vfat')
        configure_image(config)       
    finally:
        cleanup()
