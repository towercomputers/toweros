import os
import time
from datetime import datetime
import logging

from sh import (
    Command,
    mount, parted, mkdosfs, resize2fs, tee, cat,
    cp, rm, sync, rsync, chown, truncate,
    #arch_chroot, 
    tar, xz,
    losetup, 
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
    tar('-xpf', archlinux_tar_path, '-C', wd("EXPORT_ROOTFS_DIR"), _out=logger.debug)
    # put nx packages
    tar('-xpf', nx_tar_path, '-C', wd("EXPORT_ROOTFS_DIR"), _out=logger.debug)
    # put cross platform emulator
    cp('/usr/bin/qemu-arm-static', wd("EXPORT_ROOTFS_DIR/usr/bin"))
    # put and run toweros-host installer
    cp(f'{INSTALLER_DIR}/00_install_toweros_host.sh', wd("EXPORT_ROOTFS_DIR"))
    arch_chroot(wd("EXPORT_ROOTFS_DIR"), 'sh', '/00_install_toweros_host.sh', _out=logger.debug)
    # clean installation files
    rm(wd("EXPORT_ROOTFS_DIR/00_install_toweros_host.sh"))
    rm(wd("EXPORT_ROOTFS_DIR/usr/bin/qemu-arm-static"))
    nx_tar_name = os.path.basename(nx_tar_path).split(".")[0]
    rm('-rf', wd(f"EXPORT_ROOTFS_DIR/{nx_tar_name}"))
    # synchronize folder
    sync(wd("EXPORT_ROOTFS_DIR"))

@clitask("Creating RPI partitions...")
def create_rpi_partitions():
    image_file = wd("toweros-host.img")
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

def unmount_all():
    utils.lazy_umount(wd("ROOTFS_DIR/boot/"))
    utils.lazy_umount(wd("ROOTFS_DIR"))
    utils.lazy_umount(wd("EXPORT_ROOTFS_DIR"))
    losetup('-D')

@clitask("Cleaning up...")
def cleanup():
    unmount_all()
    rm('-rf', WORKING_DIR, _out=logger.debug)

@clitask("Building TowserOS-Host image...", timer_message="TowserOS-Host image built in {0}.", sudo=True)
def build_image(builds_dir):
    archlinux_tar_path = utils.prepare_required_build("arch-linux-arm", builds_dir)
    nx_tar_path = utils.prepare_required_build("nx-armv7h", builds_dir)
    user = os.getlogin()
    try:
        prepare_working_dir()
        prepare_chroot_image(archlinux_tar_path, nx_tar_path)
        create_rpi_partitions()
        loop_dev = create_loop_device(wd("toweros-host.img"))
        prepare_rpi_partitions(loop_dev)
        unmount_all()
        image_path = compress_image(builds_dir, user)
    finally:
        cleanup()
    return image_path

@clitask("Copying image {0} in device {1}...")
def copy_image(image_file, device):
    utils.unmount_all(device)
    # burn image
    tee(device, _in=cat(image_file))
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
def configure_image(config):
    logger.debug(f"Host configuration: {config}")
    # put cross platform emulator
    cp('/usr/bin/qemu-arm-static', wd("ROOTFS_DIR/usr/bin"))
    # put configuration scripts
    cp(f'{INSTALLER_DIR}/01_configure_toweros_host.sh', wd("ROOTFS_DIR/root/"))
    cp(f'{INSTALLER_DIR}/files/toweros_host_iptables.rules', wd("ROOTFS_DIR/root/"))
    # run configuration script
    args_key = [
        "HOSTNAME", "USERNAME", "PUBLIC_KEY", "PASSWORD_HASH",
        "KEYMAP", "TIMEZONE", "LANG",
        "ONLINE", "WLAN_SSID", "WLAN_SHARED_KEY",
        "THIN_CLIENT_IP", "TOWER_NETWORK"
    ]
    args = [config[key] for key in args_key]
    arch_chroot(wd("ROOTFS_DIR"), 'sh', '/root/01_configure_toweros_host.sh', *args, _out=logger.debug, _err_to_out=True)
    # update fstab
    #tee(wd("ROOTFS_DIR/etc/fstab"), _in=genfstab('-U', wd("ROOTFS_DIR")))
    Command('sh')('-c', f'genfstab -U {wd("ROOTFS_DIR")} | sed "/swap/d" | sed "/#/d" > {wd("ROOTFS_DIR/etc/fstab")}')
    # clean configuration files
    rm(wd("ROOTFS_DIR/root/01_configure_toweros_host.sh"))
    rm(wd("ROOTFS_DIR/root/toweros_host_iptables.rules"))
    rm(wd("ROOTFS_DIR/usr/bin/qemu-arm-static")) 

@clitask("Installing TowserOS-Host in {1}...", timer_message="TowserOS-Host installed in {0}.", sudo=True)
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
