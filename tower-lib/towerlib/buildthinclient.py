import logging
import os
from os import makedirs
from os.path import join as join_path
from shutil import copy as copyfile
import sys
import tempfile
import getpass

from towerlib.utils.shell import rm, git, Command, apk, cp, abuild, abuild_sign, arch, ssh, scp
from towerlib.utils.decorators import clitask
from towerlib.utils.shell import doas
from towerlib.utils.network import download_file
from towerlib.utils.disk import targz_to_image
from towerlib.__about__ import __version__
from towerlib.utils.exceptions import LockException, UnkownHost, TowerException
from towerlib.config import THINCLIENT_ALPINE_BRANCH, APK_LOCAL_REPOSITORY, TOWER_BUILDS_DIR
from towerlib import sshconf

logger = logging.getLogger('tower')

ARCH = arch().strip()

WORKING_DIR_NAME = 'build-toweros-thinclient-work'
WORKING_DIR = join_path(os.path.expanduser('~'), WORKING_DIR_NAME)
NOPYFILES_DIR = join_path(os.path.dirname(os.path.abspath(__file__)), 'nopyfiles')
REPO_PATH = os.path.abspath(join_path(os.path.dirname(__file__), '..', '..'))
ALPINE_APORT_REPO = 'https://gitlab.alpinelinux.org/alpine/aports.git'

TMP_DIR = tempfile.gettempdir()
USERNAME = getpass.getuser()

EDGE_REPO = f'https://dl-cdn.alpinelinux.org/alpine/edge/testing/{ARCH}/'
EDGE_APKS = [
    'sfwbar-1.0_beta14-r0.apk',
    'sfwbar-doc-1.0_beta14-r0.apk',
]

def wdir(path):
    return join_path(WORKING_DIR, path)


def sprint(value):
    print(value.decode("utf-8", 'ignore') if isinstance(value, bytes) else value, end='', flush=True)


def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise LockException(f"f{WORKING_DIR} already exists! Is another build in progress? If not, delete this folder and try again.")
    makedirs(WORKING_DIR)


@clitask("Cleaning up...")
def cleanup():
    rm('-rf', WORKING_DIR, _out=logger.debug)


def check_abuild_key():
    abuild_folder = join_path(os.path.expanduser('~'), '.abuild')
    abuild_conf = join_path(abuild_folder, 'abuild.conf')
    if not os.path.exists(abuild_folder) or not os.path.exists(abuild_conf):
        logger.error("ERROR: You must have an `abuild` key to build the image. Please use `abuild-keygen -a -i`.")
        sys.exit()


def download_edge_apks():
    rm('-rf', APK_LOCAL_REPOSITORY)
    makedirs(f'{APK_LOCAL_REPOSITORY}/{ARCH}')
    edge_apks = []
    for apk_file in EDGE_APKS:
        local_path = f'{APK_LOCAL_REPOSITORY}/{ARCH}/{apk_file}'
        download_file(f'{EDGE_REPO}{apk_file}', local_path)
        edge_apks.append(local_path)
    # create index
    apk_index_opts = ['index', '--arch', ARCH, '--rewrite-arch', ARCH, '--allow-untrusted']
    apk(*apk_index_opts, '-o', f'{APK_LOCAL_REPOSITORY}/{ARCH}/APKINDEX.tar.gz', '--no-warnings', *edge_apks)
    # sign index
    abuild_sign(f'{APK_LOCAL_REPOSITORY}/{ARCH}/APKINDEX.tar.gz')


@clitask("Prepare `toweros-thinclient` APK packages...")
def prepare_tower_apks():
    with doas:
        apk('update')
    # build tower-cli
    abuild('-r', '-f', _cwd=f"{REPO_PATH}/tower-apks/toweros-thinclient", _err_to_out=True, _out=logger.debug)
    abuild('-r', '-f', _cwd=f"{REPO_PATH}/tower-apks/toweros-thinclient-builds", _err_to_out=True, _out=logger.debug)


@clitask("Building thin client image, be patient...")
def prepare_image():
    # download alpine aports form gitlab
    git('clone', '--depth=1', f'--branch={THINCLIENT_ALPINE_BRANCH[1:]}-stable', ALPINE_APORT_REPO, _cwd=WORKING_DIR)
    # copy tower custom scripts
    copyfile(join_path(NOPYFILES_DIR, f'mkimg.tower-{ARCH}.sh'), wdir('aports/scripts'))
    copyfile(join_path(NOPYFILES_DIR, 'genapkovl-toweros-thinclient.sh'), wdir('aports/scripts'))
    with doas:
        apk('update')
    Command('sh')(
        wdir('aports/scripts/mkimage.sh'),
        '--arch', ARCH,
        '--outdir', WORKING_DIR,
        '--repository', APK_LOCAL_REPOSITORY,
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{THINCLIENT_ALPINE_BRANCH}/main',
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{THINCLIENT_ALPINE_BRANCH}/community',
        '--profile', f'tower',
        '--tag', __version__,
         _err_to_out=True, _out=logger.debug,
         _cwd=WORKING_DIR
    )
    image_extension = 'iso' if ARCH == 'x86_64' else 'tar.gz'
    image_src_path = wdir(f"alpine-tower-{__version__}-{ARCH}.{image_extension}")
    image_dest_path = join_path(
        TOWER_BUILDS_DIR,
        f'toweros-thinclient-{__version__}-{ARCH}.{image_extension}'
    )
    with doas:
        cp(image_src_path, image_dest_path)
    return image_dest_path


def convert_archive_to_image(image_path):
    image_extension = 'iso' if ARCH == 'x86_64' else 'tar.gz'
    if image_extension == 'iso':
        return image_path
    # convert to image
    with doas:
        targz_to_image(image_path)
    return image_path.replace('.tar.gz', '.img.gz')


@clitask("Building TowserOS-ThinClient image...", timer_message="TowserOS-ThinClient image built in {0}.", task_parent=True)
def build_image():
    image_path = None
    try:
        check_abuild_key()
        prepare_working_dir()
        download_edge_apks()
        prepare_tower_apks()
        image_path = prepare_image()
        image_path = convert_archive_to_image(image_path)
    finally:
        cleanup()
    if image_path:
        logger.info("Image ready: %s", image_path)


@clitask("Preparing host {0} for build...")
def prepare_host_for_build(build_host):
    out = {"_out": logger.debug, "_err_to_out": True}
    # clean previous install
    ssh(build_host, 'rm -rf toweros .abuild packages', **out)
    # copy toweros repo
    scp('-r', REPO_PATH, f'{build_host}:', **out)
    # install apk keys
    scp('-r', f"/home/{USERNAME}/.abuild", f'{build_host}:', **out)
    ssh(build_host, "sudo cp .abuild/*.pub /etc/apk/keys/", **out)
    # install packages
    build_depends = [
        "alpine-sdk", "xz", "rsync", "perl-utils", "musl-locales",
        "py3-pip", "py3-requests", "py3-rich", "cairo", "cairo-dev", "python3-dev",
        "gobject-introspection", "gobject-introspection-dev",
        "xsetroot", "losetup", "squashfs-tools", "xorriso", "pigz", "mtools",
    ]
    ssh(build_host, f"sudo apk update", **out)
    ssh(build_host, f"sudo apk add {' '.join(build_depends)}", **out)
    ssh(build_host, f"sudo addgroup {USERNAME} abuild", **out)
    # install tower-lib abd tower-cli
    ssh(build_host, f"sudo pip install -e toweros/tower-lib --break-system-packages", **out)
    ssh(build_host, f"sudo pip install -e toweros/tower-cli --break-system-packages --no-deps", **out)


@clitask("Transferring image from host {0} to thin client...")
def copy_image_from_host(build_host):
    out = {"_out": logger.debug, "_err_to_out": True}
    host_arch = ssh(build_host, "arch").strip()
    image_extension = 'iso' if host_arch == 'x86_64' else 'img.gz'
    archive_name = f"toweros-thinclient-{__version__}-{host_arch}.{image_extension}"
    archive_dest_path = join_path(TOWER_BUILDS_DIR, archive_name)
    scp(f"{build_host}:{archive_dest_path}", TMP_DIR, **out)
    with doas:
        cp(join_path(TMP_DIR, archive_name), TOWER_BUILDS_DIR)
    return archive_dest_path


@clitask("Building TowserOS-ThinClient image in {0}...", timer_message="TowserOS-ThinClient image built in {0}.", task_parent=True)
def build_image_in_host(build_host, verbose=False):
    if not sshconf.exists(build_host):
        raise UnkownHost(f"Host {build_host} not found.")
    if not sshconf.is_up(build_host):
        raise TowerException(f"Host {build_host} is not up.")
    # prepare host
    prepare_host_for_build(build_host)
    # build image
    verbose_opt = "--verbose" if verbose else ""
    ssh(
        '-t', build_host,
        f"cd toweros/tower-build-cli && ./tower-build {verbose_opt} thinclient",
        _err=sprint, _out=sprint, _in=sys.stdin,
        _out_bufsize=0, _err_bufsize=0,
    )
    image_path = copy_image_from_host(build_host)
    logger.info("Image ready: %s", image_path)
