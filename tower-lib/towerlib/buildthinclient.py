import logging
import os
from os import makedirs
from os.path import join as join_path
from shutil import copy as copyfile
import sys
import tempfile
import getpass

from towerlib.utils.shell import rm, git, Command, apk, cp, abuild, abuild_sign, runuser, ssh, scp
from towerlib.utils.decorators import clitask
from towerlib.utils.shell import doas
from towerlib.utils.network import download_file
from towerlib.__about__ import __version__
from towerlib.utils.exceptions import LockException
from towerlib.config import THINCLIENT_ALPINE_BRANCH, APK_LOCAL_REPOSITORY, TOWER_BUILDS_DIR

logger = logging.getLogger('tower')

#ARCH = 'x86_64'
ARCH = "aarch64"

WORKING_DIR_NAME = 'build-toweros-thinclient-work'
WORKING_DIR = join_path(os.path.expanduser('~'), WORKING_DIR_NAME)
NOPYFILES_DIR = join_path(os.path.dirname(os.path.abspath(__file__)), 'nopyfiles')
REPO_PATH = os.path.abspath(join_path(os.path.dirname(__file__), '..', '..'))
ALPINE_APORT_REPO = 'https://gitlab.alpinelinux.org/alpine/aports.git'

TMP_DIR = tempfile.gettempdir()
BUILDER_HOST = "rpi5"
USERNAME = getpass.getuser()

EDGE_REPO = f'https://dl-cdn.alpinelinux.org/alpine/edge/testing/{ARCH}/'
EDGE_APKS = [
    'sfwbar-1.0_beta14-r0.apk',
    'sfwbar-doc-1.0_beta14-r0.apk',
]

def wdir(path):
    return join_path(WORKING_DIR, path)


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


@clitask("Prepare Tower CLI APK package...")
def prepare_tower_apk():
    if ARCH == 'x86_64':
        with doas:
            apk('update')
        # build tower-cli
        abuild('-r', _cwd=f"{REPO_PATH}/tower-apks/toweros-thinclient", _err_to_out=True, _out=logger.debug)
    else:
        prepare_tower_arm_apk()

def prepare_tower_arm_apk():
    out = {"_out": logger.debug, "_err_to_out": True}
    # install abuild
    ssh(BUILDER_HOST, 'sudo apk add alpine-sdk', **out)
    ssh(BUILDER_HOST, f'sudo addgroup {USERNAME} abuild', **out)
    # clean previous build
    ssh(BUILDER_HOST, 'rm -rf .abuild toweros packages', **out)
    # copy toweros repo
    scp('-r', f'{REPO_PATH}', f'{BUILDER_HOST}:', **out)
    # copy abuild key
    scp('-r', f'/home/{USERNAME}/.abuild', f'{BUILDER_HOST}:', **out)
    ssh(BUILDER_HOST, 'sudo cp .abuild/*.pub /etc/apk/keys/', **out)
    # copy edge apks
    ssh(BUILDER_HOST, 'mkdir -p packages/tower-apks/')
    scp('-r', f'{APK_LOCAL_REPOSITORY}/{ARCH}', f'{BUILDER_HOST}:packages/tower-apks/', **out)
    ssh(BUILDER_HOST, 'sudo cp /etc/apk/repositories /etc/apk/repositories.bak')
    ssh(BUILDER_HOST, f"echo '/home/{USERNAME}/packages/tower-apks/' | sudo tee -a /etc/apk/repositories")
    # update apk index
    ssh(BUILDER_HOST, 'sudo apk update', **out)
    # build toweros-thinclient
    ssh(BUILDER_HOST, 'cd toweros/tower-apks/toweros-thinclient && abuild -r', **out)
    # copy apk to local repo
    scp(f'{BUILDER_HOST}:packages/tower-apks/{ARCH}/toweros-thinclient-{__version__}-r0.apk', TMP_DIR, **out)
    cp(f'{TMP_DIR}/toweros-host-{__version__}-r0.apk', f'{APK_LOCAL_REPOSITORY}/{ARCH}')
    # restore apk repositories
    ssh(BUILDER_HOST, 'sudo mv /etc/apk/repositories.bak /etc/apk/repositories')

@clitask("Building thin client image, be patient...")
def prepare_image():
    # download alpine aports form gitlab
    git('clone', '--depth=1', f'--branch={THINCLIENT_ALPINE_BRANCH[1:]}-stable', ALPINE_APORT_REPO, _cwd=WORKING_DIR)
    # copy tower custom scripts
    copyfile(join_path(NOPYFILES_DIR, 'mkimg.tower.sh'), wdir('aports/scripts'))
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
        '--profile', 'tower',
        '--tag', __version__,
         _err_to_out=True, _out=logger.debug,
         _cwd=WORKING_DIR
    )
    image_src_path = wdir(f"alpine-tower-{__version__}-{ARCH}.iso")
    image_dest_path = join_path(
        TOWER_BUILDS_DIR,
        f'toweros-thinclient-{__version__}-{ARCH}.iso'
    )
    with doas:
        cp(image_src_path, image_dest_path)
    return image_dest_path


@clitask("Building TowserOS-ThinClient image...", timer_message="TowserOS-ThinClient image built in {0}.", task_parent=True)
def build_image():
    image_path = None
    try:
        check_abuild_key()
        prepare_working_dir()
        download_edge_apks()
        prepare_tower_apk()
        image_path = prepare_image()
    finally:
        cleanup()
    if image_path:
        logger.info("Image ready: %s", image_path)
