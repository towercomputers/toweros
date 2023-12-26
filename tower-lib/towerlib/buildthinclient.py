from datetime import datetime
import logging
import os
from os import makedirs
from os.path import join as join_path
from shutil import copy as copyfile
import sys
import glob

from towerlib.utils.shell import rm, git, Command, apk, cp, abuild, abuild_sign
from towerlib.utils.decorators import clitask
from towerlib.utils.shell import doas
from towerlib import buildhost
from towerlib.__about__ import __version__
from towerlib.utils.exceptions import LockException
from towerlib.config import THINCLIENT_ALPINE_BRANCH, APK_LOCAL_REPOSITORY, TOWER_BUILDS_DIR

logger = logging.getLogger('tower')

WORKING_DIR_NAME = 'build-toweros-thinclient-work'
WORKING_DIR = join_path(os.path.expanduser('~'), WORKING_DIR_NAME)
INSTALLER_DIR = join_path(os.path.dirname(os.path.abspath(__file__)), '..', 'toweros-installers', 'toweros-thinclient')
REPO_PATH = join_path(os.path.dirname(os.path.abspath(__file__)), '..', '..')
ALPINE_APORT_REPO = 'https://gitlab.alpinelinux.org/alpine/aports.git'

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


@clitask("Prepare Tower CLI APK package...")
def prepare_tower_apk():
    with doas:
        apk('update')
    rm('-rf', APK_LOCAL_REPOSITORY)
    abuild('-r', _cwd=REPO_PATH, _err_to_out=True, _out=logger.debug)
    """ edges_apks = glob.glob(f'{INSTALLER_DIR}/alpine-edge/x86_64/*.apk')
    for apk_path in edges_apks:
        cp(apk_path, f'{APK_LOCAL_REPOSITORY}/x86_64/')
    edges_apks = glob.glob(f'{APK_LOCAL_REPOSITORY}/x86_64/*.apk')
    apk('index', '-o', f'{APK_LOCAL_REPOSITORY}/x86_64/APKINDEX.tar.gz', '--allow-untrusted', *edges_apks)
    abuild_sign(f'{APK_LOCAL_REPOSITORY}/x86_64/APKINDEX.tar.gz') """


@clitask("Building Thin Client image, be patient...")
def prepare_image():
    # download alpine aports form gitlab
    git('clone', '--depth=1', f'--branch={THINCLIENT_ALPINE_BRANCH[1:]}-stable', ALPINE_APORT_REPO, _cwd=WORKING_DIR)
    # copy tower custom scripts
    copyfile(join_path(INSTALLER_DIR, 'mkimg.tower.sh'), wdir('aports/scripts'))
    copyfile(join_path(INSTALLER_DIR, 'genapkovl-tower-thinclient.sh'), wdir('aports/scripts'))
    with doas:
        apk('update')
    Command('sh')(
        wdir('aports/scripts/mkimage.sh'),
        '--outdir', WORKING_DIR,
        '--repository', APK_LOCAL_REPOSITORY,
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{THINCLIENT_ALPINE_BRANCH}/main',
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/{THINCLIENT_ALPINE_BRANCH}/community',
        '--profile', 'tower',
        '--tag', __version__,
         _err_to_out=True, _out=logger.debug,
         _cwd=WORKING_DIR
    )
    image_src_path = wdir(f"alpine-tower-{__version__}-x86_64.iso")
    image_dest_path = join_path(
        TOWER_BUILDS_DIR,
        datetime.now().strftime(f'toweros-thinclient-{__version__}-%Y%m%d%H%M%S-x86_64.iso')
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
        prepare_tower_apk()
        image_path = prepare_image()
    finally:
        cleanup()
    if image_path:
        logger.info("Image ready: %s", image_path)
