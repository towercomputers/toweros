from datetime import datetime
import logging
import os
from os import makedirs
from os.path import join as join_path
import glob
from shutil import copytree, copy as copyfile
import sys

import sh
from sh import rm, git, pip, Command, apk


from tower.utils import clitask
from tower import buildhost
from tower.__about__ import __version__

logger = logging.getLogger('tower')

TOWER_TOOLS_URL = "git+ssh://github.com/towercomputing/toweros.git"
# TODO: test v3.19 on release
ALPINE_BRANCH = "3.18"

WORKING_DIR_NAME = 'build-toweros-thinclient-work'
WORKING_DIR = join_path(os.path.expanduser('~'), WORKING_DIR_NAME)
INSTALLER_DIR = join_path(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'toweros-thinclient')
HOME_PATH = join_path(os.path.dirname(os.path.abspath(__file__)), '..')

def wd(path):
    return join_path(WORKING_DIR, path)

def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise Exception(f"f{WORKING_DIR} already exists! Is another build in progress? if not, delete this folder and try again.")
    makedirs(WORKING_DIR)

@clitask("Cleaning up...")
def cleanup():
    rm('-rf', WORKING_DIR, _out=logger.debug)

def find_tower_tools(builds_dir):
    wheels = glob.glob(join_path(builds_dir, 'tower_tools-*.whl'))
    tower_tools_wheel_path = f"file://{wheels.pop()}" if wheels else TOWER_TOOLS_URL
    return tower_tools_wheel_path

def find_host_image(builds_dir):
    host_images = glob.glob(join_path(builds_dir, 'toweros-host-*.xz'))
    if not host_images:
        logger.info("Host image not found in builds directory. Building a new image.")
        rpi_image_path = buildhost.build_image(builds_dir)
    else:
        rpi_image_path = host_images.pop()
        logger.info(f"Using host image {rpi_image_path}")
    return rpi_image_path

def find_readme():
    readme_path = join_path(HOME_PATH, 'README.md')
    if os.path.exists(readme_path):
        return readme_path
    readme_path = join_path(HOME_PATH, 'docs', 'README.md')
    if os.path.exists(readme_path):
        return readme_path
    readme_path = "/var/towercomputers/docs/README.md"
    if os.path.exists(readme_path):
        return readme_path
    raise Exception("README.md not found!")

def check_abuild_key():
    abuild_folder = join_path(os.path.expanduser('~'), '.abuild')
    abuild_conf = join_path(abuild_folder, 'abuild.conf')
    if not os.path.exists(abuild_folder) or not os.path.exists(abuild_conf):
        logger.error("ERROR: You must have an abuild key to build the image. Please use `abuild-keygen -a -i`.")
        sys.exit()

@clitask("Downloading pip packages...")
def prepare_pip_packages(builds_dir):
    makedirs(wd('overlay/var/cache/pip-packages'))
    tower_tools_wheel_path = TOWER_TOOLS_URL
    wheels = glob.glob(join_path(builds_dir, 'tower_tools-*.whl'))
    if wheels:
        wheel = wheels.pop()
        tower_tools_wheel_path = f"file://{wheel}"
        copyfile(wheel, wd('overlay/var/cache/pip-packages'))
    pip(
        "download", f"tower-tools @ {tower_tools_wheel_path}", 
        '-d', wd('overlay/var/cache/pip-packages'),
        _err_to_out=True, _out=logger.debug
    )

def prepare_installer():
    makedirs(wd('overlay/var/towercomputers/'))
    copytree(join_path(INSTALLER_DIR, 'installer'), wd('overlay/var/towercomputers/installer'))

def prepare_docs():
    makedirs(wd('overlay/var/towercomputers/docs'))
    readme_path = find_readme()
    copyfile(readme_path, wd('overlay/var/towercomputers/docs'))
    copyfile(join_path(HOME_PATH, 'docs', 'src', 'TowerOS Whitepaper.pdf'), wd('overlay/var/towercomputers/docs'))

def prepare_build(builds_dir):
    makedirs(wd('overlay/var/towercomputers/builds'))
    host_image_path = find_host_image(builds_dir)
    copyfile(host_image_path, wd('overlay/var/towercomputers/builds'))
    wheels = glob.glob(join_path(wd('overlay/var/cache/pip-packages'), 'tower_tools-*.whl'))
    copyfile(wheels[0], wd('overlay/var/towercomputers/builds'))

def prepare_etc_folder():
    copytree(join_path(INSTALLER_DIR, 'etc'), wd('overlay/etc'))

def prepare_overlay(builds_dir):
    prepare_pip_packages(builds_dir)
    prepare_installer()
    prepare_docs()
    prepare_etc_folder()
    prepare_build(builds_dir)

@clitask("Building image, be patient...")
def prepare_image(builds_dir):
    git('clone', '--depth=1', f'--branch={ALPINE_BRANCH}-stable', 'https://gitlab.alpinelinux.org/alpine/aports.git', _cwd=WORKING_DIR)
    copyfile(join_path(INSTALLER_DIR, 'mkimg.tower.sh'), wd('aports/scripts'))
    copyfile(join_path(INSTALLER_DIR, 'genapkovl-tower-thinclient.sh'), wd('aports/scripts'))
    copyfile(join_path(INSTALLER_DIR, 'etc', 'apk', 'world'), wd('aports/scripts'))
    with sh.contrib.sudo(password="", _with=True):
        apk('update')
    Command('sh')(
        wd('aports/scripts/mkimage.sh'),
        '--outdir', WORKING_DIR,
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/v{ALPINE_BRANCH}/main',
        '--repository', f'http://dl-cdn.alpinelinux.org/alpine/v{ALPINE_BRANCH}/community',
        '--profile', 'tower',
        '--tag', __version__,
         _err_to_out=True, _out=logger.debug,
         _cwd=WORKING_DIR
    )
    image_src_path = wd(f"alpine-tower-{__version__}-x86_64.iso")
    image_dest_path = join_path(
        builds_dir, 
        datetime.now().strftime(f'toweros-thinclient-{__version__}-%Y%m%d%H%M%S-x86_64.iso')
    )
    copyfile(image_src_path, image_dest_path)
    return image_dest_path
    

@clitask("Building TowserOS-ThinClient image...", timer_message="TowserOS-ThinClient image built in {0}.", task_parent=True)
def build_image(builds_dir):
    image_path = None
    try:
        check_abuild_key()
        prepare_working_dir()
        prepare_overlay(builds_dir)
        image_path = prepare_image(builds_dir)
    finally:
        cleanup()
    if image_path:
        logger.info(f"Image ready: {image_path}")
