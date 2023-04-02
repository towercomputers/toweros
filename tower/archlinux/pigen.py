import os
import time
from datetime import datetime, timedelta
import logging
import math

import sh
from sh import (
    Command, ErrorReturnCode,
    mount, umount, parted, mkdosfs,
    cp, rm, sync, rsync, chown, truncate, mkdir, ls,
    arch_chroot, 
    bsdtar, xz,
    losetup, 
)
mkfs_ext4 = Command('mkfs.ext4')

from tower import osutils

logger = logging.getLogger('tower')

WORKING_DIR = os.path.join(os.getcwd(), 'buildtowerpi-work')
INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'installer')

def withinfo(message):
    def decorator(function):
        def new_function(*args, **kwargs):
            start_time = time.time()
            logger.info(message)
            ret = function(*args, **kwargs)
            duration = timedelta(seconds=time.time() - start_time)
            logger.info(f"Done in {duration}.")
            return ret
        return new_function
    return decorator

def wd(path):
    return os.path.join(WORKING_DIR, path)

def prepare_working_dir():
    rm('-rf', WORKING_DIR)
    os.makedirs(WORKING_DIR)

@withinfo("Preparing Arch Linux system...")
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
    cp(f'{INSTALLER_DIR}/install_towerospi.sh', wd("EXPORT_ROOTFS_DIR"))
    arch_chroot(wd("EXPORT_ROOTFS_DIR"), 'sh', '/install_towerospi.sh', _out=logger.debug)
    # clean installation files
    rm(wd("EXPORT_ROOTFS_DIR/install_towerospi.sh"))
    rm(wd("EXPORT_ROOTFS_DIR/usr/bin/qemu-arm-static"))
    nx_tar_name = os.path.basename(archlinux_tar_path).split(".")[0]
    rm('-rf', wd(f"EXPORT_ROOTFS_DIR/{nx_tar_name}"))
    # synchronize folder
    sync(wd("EXPORT_ROOTFS_DIR"))

@withinfo("Creating RPI partitions...")
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

@withinfo("Copying Arch Linux system in RPI partitions...")
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

@withinfo("Compressing image with xz...")
def compress_image(owner):
    image_name = os.path.join(os.getcwd(), datetime.now().strftime('towerospi-%Y%m%d%H%M%S.img.xz'))
    xz(
        '--compress', '--force', 
        '--threads', 0, '--memlimit-compress=90%', '--best',
	    '--stdout', wd("toweros-pi.img"),
        _out=image_name
    )
    chown(f"{owner}:{owner}", image_name)
    logger.info(f"Image ready: {image_name}") 

def force_umount(path, retry=0):
    if not os.path.exists(path):
        return
    try:
        umount(path, _out=logger.debug)
    except sh.ErrorReturnCode_32: # target is busy
        if retry < 3:
            logger.info(f"{path} is busy. Please wait 3 seconds!")
            time.sleep(3)
            force_umount(path, retry=retry+1)
    except ErrorReturnCode:
        pass

def unmount_all():
    force_umount(wd("ROOTFS_DIR/boot/"))
    force_umount(wd("ROOTFS_DIR"))
    force_umount(wd("EXPORT_ROOTFS_DIR"))
    losetup('-D')

@withinfo("Cleaning up...")
def cleanup():
    unmount_all()
    rm('-rf', WORKING_DIR, _out=logger.debug)

@withinfo("Building TowserOS PI image...")
def build_image(archlinux_tar_path, nx_tar_path):
    user = os.getlogin()
    with sh.contrib.sudo(password="", _with=True):
        try:
            prepare_working_dir()
            prepare_chroot_image(archlinux_tar_path, nx_tar_path)
            create_rpi_partitions()
            loop_dev = create_loop_device(wd("toweros-pi.img"))
            prepare_rpi_partitions(loop_dev)
            unmount_all()
            compress_image(user)
        finally:
            cleanup()

@withinfo("Configuring TowserOS PI image...")
def configure_image(device, config):
    logger.info("\n".join([f'{key}="{value}"' for key, value in config.items()]))
    with sh.contrib.sudo(password="", _with=True):
        chroot_process = None
        try:
            osutils.unmount_all(device)
            prepare_working_dir()
            boot_part = Command('sh')('-c', f'ls {device}*1').strip()
            root_part = Command('sh')('-c', f'ls {device}*2').strip()
            mount('--mkdir', root_part, wd("ROOTFS_DIR"), '-t', 'ext4')
            mount('--mkdir', boot_part, wd("ROOTFS_DIR/boot/"), '-t', 'vfat')
            # put cross platform emulator
            cp('/usr/bin/qemu-arm-static', wd("ROOTFS_DIR/usr/bin"))
            # put configuration scripts
            cp(f'{INSTALLER_DIR}/configure_towerospi.sh', wd("ROOTFS_DIR/root/"))
            cp(f'{INSTALLER_DIR}/towerospi-iptables.rules', wd("ROOTFS_DIR/root/"))

            args_key = [
                "HOSTNAME", "USERNAME", "PUBLIC_KEY", "ENCRYPTED_PASSWORD",
                "KEYMAP", "TIMEZONE", "LANG",
                "ONLINE", "WLAN_SSID", "WLAN_SHARED_KEY", "WLAN_COUNTRY",
                "THIN_CLIENT_IP", "TOWER_NETWORK"
            ]
            # run configuration script
            args = [config[key] for key in args_key]
            chroot_process = arch_chroot(wd("ROOTFS_DIR"), 'sh', '/root/configure_towerospi.sh', *args, _out=logger.debug, _err_to_out=True)
            # clean configuration files
            rm(wd("ROOTFS_DIR/root/configure_towerospi.sh"))
            rm(wd("ROOTFS_DIR/root/towerospi-iptables.rules"))
            rm(wd("ROOTFS_DIR/usr/bin/qemu-arm-static"))            
        finally:
            if chroot_process:
                chroot_process.terminate()
            cleanup()
