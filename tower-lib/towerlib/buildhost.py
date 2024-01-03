import os
import time
from datetime import datetime
import logging
import glob
import getpass
import tempfile
from io import StringIO

from towerlib.utils.shell import (
    Command, ErrorReturnCode,
    mount, parted, mkdosfs, tee, cat, echo,
    cp, rm, sync, rsync, chown, truncate, mkdir,
    tar, xz, apk, dd,
    losetup, abuild_sign, openssl,
    scp, ssh, runuser,
)

from towerlib import utils, config, sshconf
from towerlib.utils import clitask
from towerlib.__about__ import __version__
from towerlib.config import TOWER_DIR, HOST_ALPINE_BRANCH, APK_LOCAL_REPOSITORY
from towerlib.utils.exceptions import LockException, BuildException

mkfs_ext4 = Command('mkfs.ext4')
fsck_ext4 = Command('fsck.ext4')

logger = logging.getLogger('tower')

WORKING_DIR = os.path.join(os.path.expanduser('~'), 'build-toweros-host-work')
NOPYFILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nopyfiles')
REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
TMP_DIR = tempfile.gettempdir()

BUILDER_HOST = "builder"
USERNAME = getpass.getuser()
ARCH = "aarch64"

def sprint(value):
    print(value, end='', flush=True)


def wdir(path):
    return os.path.join(WORKING_DIR, path)


def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise LockException(f"f{WORKING_DIR} already exists! Is another build in progress? If not, delete this folder and try again.")
    os.makedirs(WORKING_DIR)


def fetch_apk_packages(repo_path, branch, packages):
    apk(
        'fetch', '--arch', ARCH, '-R', '--url', '--no-cache', '--allow-untrusted',
        '--root', wdir("EXPORT_BOOTFS_DIR"),
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{branch}/main',
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{branch}/community',
        '-o', repo_path, *packages, _out=logger.debug
    )


def download_apk_packages(repo_path):
    world_path = os.path.join(REPO_PATH, 'tower-apks', 'toweros-host', 'world')
    apks = []
    for line in cat(world_path, _iter=True):
        package = line.strip()
        if package.startswith('linux-firmware-brcm-cm4'):
            continue
        apks.append(line.strip())
    # download packages
    fetch_apk_packages(repo_path, HOST_ALPINE_BRANCH, apks)


def build_brcrm_cm4_apk(repo_path):
    # build and copy linux-firmware-brcm-cm4
    Command('sh')(
        '-c',
        f'runuser -u {USERNAME} -- abuild -r',
        _cwd=f"{REPO_PATH}/tower-apks/linux-firmware-brcm-cm4"
    )
    cp(f"{APK_LOCAL_REPOSITORY}/x86_64/linux-firmware-brcm-cm4-1.0-r0.apk", repo_path)


def build_toweros_host_apk(repo_path):
    out = {"_out": logger.debug, "_err_to_out": True}
    with runuser.bake('-u', USERNAME, '--'):
        ssh(BUILDER_HOST, 'sudo apk add alpine-sdk', **out)
        ssh(BUILDER_HOST, f'sudo addgroup {USERNAME} abuild', **out)
        ssh(BUILDER_HOST, 'rm -rf .abuild tower-apks tower-lib', **out)
        scp('-r', f'{REPO_PATH}/tower-apks', f'{BUILDER_HOST}:', **out)
        scp('-r', f'{REPO_PATH}/tower-lib', f'{BUILDER_HOST}:', **out)
        scp('-r', f'/home/{USERNAME}/.abuild', f'{BUILDER_HOST}:', **out)
        ssh(BUILDER_HOST, 'sudo cp .abuild/*.pub /etc/apk/keys/', **out)
        ssh(BUILDER_HOST, 'cd tower-apks/toweros-host && abuild -r', **out)
        scp(f'{BUILDER_HOST}:packages/tower-apks/{ARCH}/toweros-host-{__version__}-r0.apk', TMP_DIR, **out)
    cp(f'{TMP_DIR}/toweros-host-{__version__}-r0.apk', repo_path)


def prepare_apk_repos(private_key_path):
    repo_path = wdir(f"EXPORT_BOOTFS_DIR/apks/{ARCH}/")
    rm('-rf', repo_path)
    mkdir('-p',repo_path)
    # download packages
    build_toweros_host_apk(repo_path)
    download_apk_packages(repo_path)
    build_brcrm_cm4_apk(repo_path)
    # prepare index
    apks = glob.glob(wdir(f"EXPORT_BOOTFS_DIR/apks/{ARCH}/*.apk"))
    apk_index_path = wdir(f"EXPORT_BOOTFS_DIR/apks/{ARCH}/APKINDEX.tar.gz")
    apk_index_opts = ['index', '--arch', ARCH, '--rewrite-arch', ARCH, '--allow-untrusted']
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
        '--', wdir("root.img"), '4G',
        _out=logger.debug
    )
    # mount image in temporary folder
    mkdir('-p', wdir("EXPORT_BOOTFS_DIR"))
    mount(wdir("root.img"), wdir("EXPORT_BOOTFS_DIR"))
    # put alpine linux files
    tar('-xpf', alpine_tar_path, '-C', wdir("EXPORT_BOOTFS_DIR"))
    prepare_apk_repos(private_key_path)
    # synchronize folder
    sync(wdir("EXPORT_BOOTFS_DIR"))


def prepare_overlay(pub_key_path):
    # put public key used to signe apk index
    mkdir('-p', wdir("overlay/etc/apk/keys/"))
    cp(pub_key_path, wdir(f"overlay/etc/apk/keys/{os.path.basename(pub_key_path)}"))
    # generate the overlay in the boot folder
    Command('sh')(
        os.path.join(NOPYFILES_DIR, 'genapkovl-toweros-host.sh'),
        wdir("overlay"),
        _cwd=wdir("EXPORT_BOOTFS_DIR/"),
        _out=print
    )
    tee(wdir("EXPORT_BOOTFS_DIR/usercfg.txt"), _in=echo("dtoverlay=dwc2,dr_mode=host"))


@clitask("Creating RPI partitions...")
def create_rpi_boot_partition():
    image_file = wdir("toweros-host.img")
    # caluclate sizes
    boot_size = 512 * 1024 * 1024
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
    mkdir('-p', wdir("BOOTFS_DIR"), _out=logger.debug)
    mount('-v', boot_dev, wdir("BOOTFS_DIR"), '-t', 'vfat')
    # copy system in partitions
    rsync('-rtxv', wdir("EXPORT_BOOTFS_DIR/"), wdir("BOOTFS_DIR/"), _out=logger.debug)


@clitask("Compressing image with xz...")
def compress_image(build_dir):
    image_name = datetime.now().strftime(f'toweros-host-{__version__}-%Y%m%d%H%M%S.img.xz')
    tmp_image_path = os.path.join(tempfile.gettempdir(), image_name)
    image_path = os.path.join(build_dir or config.TOWER_BUILDS_DIR, image_name)
    xz(
        '--compress', '--force',
        '--threads', 0, '--memlimit-compress=90%', '--best',
	    '--stdout', wdir("toweros-host.img"),
        _out=tmp_image_path
    )
    cp(tmp_image_path, image_path)
    chown(f"{USERNAME}:{USERNAME}", image_path)
    return image_path


@clitask("Copying image...")
def copy_image(build_dir):
    image_path = os.path.join(build_dir or config.TOWER_BUILDS_DIR, datetime.now().strftime(f'toweros-host-{__version__}-%Y%m%d%H%M%S.img'))
    cp(wdir("toweros-host.img"), image_path)
    chown(f"{USERNAME}:{USERNAME}", image_path)
    return image_path


def unmount_all():
    utils.lazy_umount(wdir("BOOTFS_DIR"))
    utils.lazy_umount(wdir("EXPORT_BOOTFS_DIR"))
    losetup('-D')


@clitask("Cleaning up...")
def cleanup():
    unmount_all()
    rm('-rf', WORKING_DIR, _out=logger.debug)


def prepare_apk_key():
    mkdir('-p', wdir("apk-keys"))
    private_key_path = wdir("apk-keys/tower.rsa")
    public_key_path = wdir("apk-keys/tower.rsa.pub")
    openssl('genrsa', '-out', private_key_path, '2048')
    openssl('rsa', '-in', private_key_path, '-pubout', '-out', public_key_path)
    return private_key_path, public_key_path


@clitask("Building TowerOS-Host image...", timer_message="TowserOS-Host image built in {0}.", sudo=True, task_parent=True)
def build_image(uncompressed=False, build_dir=None):
    alpine_tar_path = utils.download_alpine_rpi()
    loop_dev = None
    image_path = None
    try:
        prepare_working_dir()
        private_key_path, public_key_path = prepare_apk_key()
        prepare_system_image(alpine_tar_path, private_key_path)
        prepare_overlay(public_key_path)
        create_rpi_boot_partition()
        loop_dev = create_loop_device(wdir("toweros-host.img"))
        prepare_rpi_partitions(loop_dev)
        unmount_all()
        if uncompressed:
            image_path = copy_image(build_dir)
        else:
            image_path = compress_image(build_dir)
    finally:
        cleanup()
    if image_path:
        logger.info("Image ready: %s", image_path)
    return image_path


@clitask("Copying {0} in {1}...")
def copy_image_in_device(image_file, device):
    utils.unmount_all(device)
    # burn image
    try:
        buf = StringIO()
        dd(f'if={image_file}', f'of={device}', 'bs=8M', _out=buf)
    except ErrorReturnCode as exc:
        error_message = "Error copying image. Please check the boot device integrity and try again with the flag `--zero-device`."
        logger.error(buf.getvalue())
        logger.error(error_message)
        raise BuildException(error_message) from exc
    # determine partition name
    boot_part = Command('sh')('-c', f'ls {device}*1').strip()
    if not boot_part:
        raise BuildException("Invalid partitions")
    return boot_part


@clitask("Zeroing {0} please be patient...")
def zeroing_device(device):
    dd('if=/dev/zero', f'of={device}', 'bs=8M', _out=logger.debug)


@clitask("Configuring image...")
def insert_tower_env(boot_part, host_config):
    # mount boot partition
    mkdir('-p', wdir("BOOTFS_DIR/"))
    mount(boot_part, wdir("BOOTFS_DIR/"), '-t', 'vfat')
    str_env = "\n".join([f"{key}='{value}'" for key, value in host_config.items()])
    # insert tower.env file in boot partition
    tee(wdir("BOOTFS_DIR/tower.env"), _in=echo(str_env))
    # insert luks key in boot partition
    keys_path = os.path.join(TOWER_DIR, 'hosts', host_config['HOSTNAME'], "crypto_keyfile.bin")
    cp(keys_path, wdir("BOOTFS_DIR/crypto_keyfile.bin"))
    # insert host ssh keys in boot partition
    for key_type in ['ecdsa', 'rsa', 'ed25519']:
        host_keys_path = os.path.join(TOWER_DIR, 'hosts', host_config['HOSTNAME'], f"ssh_host_{key_type}_key")
        cp(host_keys_path, wdir(f"BOOTFS_DIR/ssh_host_{key_type}_key"))
        cp(f"{host_keys_path}.pub", wdir(f"BOOTFS_DIR/ssh_host_{key_type}_key.pub"))


@clitask("Installing TowserOS-Host on {1}...", timer_message="TowserOS-Host installed in {0}.", sudo=True, task_parent=True)
def burn_image(image_file, device, new_config, zero_device=False):
    try:
        # make sure the password is not stored in th sd-card
        host_config = {**new_config}
        if 'PASSWORD' in host_config:
            del host_config['PASSWORD']
        prepare_working_dir()
        if zero_device:
            zeroing_device(device)
        boot_part = copy_image_in_device(image_file, device)
        insert_tower_env(boot_part, host_config)
    finally:
        cleanup()


@clitask("Transfering image {0} to host `{1}`...")
def copy_image_to_host(image_file, host):
    scp(image_file, f'{host}:')

@clitask("Zeroing {0} please be patient...")
def zero_device_in_host(host, device):
    ssh(host, f'sudo dd if=/dev/zero of={device} bs=8M')

@clitask("Burning image {1} in `{2}`...")
def copy_image_in_host_device(host, image_file, device):
    try:
        buf = StringIO()
        ssh(host, f'sudo dd if={os.path.basename(image_file)} of={device} bs=8M', _out=buf, _err_to_out=True)
    except ErrorReturnCode as exc:
        error_message = "Error copying image. Please check the boot device integrity and try again with the flag `--zero-device`."
        logger.error(buf.getvalue())
        logger.error(error_message)
        raise BuildException(error_message) from exc
    # determine partition name
    boot_part = ssh(host, f"sh -c 'ls {device}*1'").strip()
    if not boot_part:
        raise BuildException("Invalid partitions")
    return boot_part


@clitask("Configuring image...")
def insert_tower_env_in_host(host, boot_part, host_config):
    debug_args = {"_out": logger.debug, "_err_to_out": True}
    # mount boot partition
    ssh(host, 'sudo mkdir -p /boot', **debug_args)
    ssh(host, f'sudo mount {boot_part} /boot -t vfat',**debug_args)
    str_env = "\n".join([f"{key}='{value}'" for key, value in host_config.items()])
    # insert tower.env file in boot partition
    tee(wdir("tower.env"), _in=echo(str_env))
    scp(wdir("tower.env"), f'{host}:', **debug_args)
    ssh(host, 'sudo cp tower.env /boot/tower.env', **debug_args)
    # insert luks key in boot partition
    keys_path = os.path.join(TOWER_DIR, 'hosts', host, "crypto_keyfile.bin")
    scp(keys_path, f'{host}:', **debug_args)
    ssh(host, 'sudo cp crypto_keyfile.bin /boot/crypto_keyfile.bin', **debug_args)
    # insert host ssh keys in boot partition
    for key_type in ['ecdsa', 'rsa', 'ed25519']:
        host_keys_path = os.path.join(TOWER_DIR, 'hosts', host_config['HOSTNAME'], f"ssh_host_{key_type}_key")
        scp(host_keys_path, f'{host}:', **debug_args)
        ssh(host, f'sudo cp ssh_host_{key_type}_key /boot/ssh_host_{key_type}_key', **debug_args)
        scp(f"{host_keys_path}.pub", f'{host}:', **debug_args)
        ssh(host, f'sudo cp ssh_host_{key_type}_key.pub /boot/ssh_host_{key_type}_key.pub', **debug_args)
    ssh(host, 'sudo umount /boot', **debug_args)
    ssh(host, 'sudo rm -rf /boot', **debug_args)


@clitask("Rebooting host `{0}`...")
def reboot_host(host):
    ssh(host, "sudo reboot")
    while sshconf.is_up(host):
        time.sleep(1)


@clitask("Installing TowserOS-Host on {1}...", timer_message="TowserOS-Host installed in {0}.", task_parent=True) 
def burn_image_in_host(host, image_file, device, new_config, zero_device=False):
    try:
        # make sure the password is not stored in th sd-card
        host_config = {**new_config}
        if 'PASSWORD' in host_config:
            del host_config['PASSWORD']
        prepare_working_dir()
        # move image to host and copy it in device
        ssh(host, 'sudo umount /boot', _ok_code=[0, 1])
        if zero_device:
            zero_device_in_host(host, device)
        copy_image_to_host(image_file, host)
        boot_part = copy_image_in_host_device(host, image_file, device)
        insert_tower_env_in_host(host, boot_part, host_config)
        reboot_host(host)
    finally:
        cleanup()