from datetime import datetime
import logging
import os
import glob
import shutil

from sh import rm, git, pip, abuild, Command

from tower.utils import clitask
from tower import buildhost
from tower.__about__ import __version__

logger = logging.getLogger('tower')

TOWER_TOOLS_URL = "git+ssh://github.com/towercomputing/tools.git"

WORKING_DIR_NAME = 'build-toweros-thinclient-work'
WORKING_DIR = os.path.join(os.path.expanduser('~'), WORKING_DIR_NAME)
INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'toweros-thinclient')
HOME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

def wd(path):
    return os.path.join(WORKING_DIR, path)

def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise Exception(f"f{WORKING_DIR} already exists! Is another build in progress? if not, delete this folder and try again.")
    os.makedirs(WORKING_DIR)

@clitask("Cleaning up...")
def cleanup():
    rm('-rf', WORKING_DIR, _out=logger.debug)

def find_tower_tools(builds_dir):
    wheels = glob.glob(os.path.join(builds_dir, 'tower_tools-*.whl'))
    tower_tools_wheel_path = f"file://{wheels.pop()}" if wheels else TOWER_TOOLS_URL
    return tower_tools_wheel_path

def find_host_image(builds_dir):
    host_images = glob.glob(os.path.join(builds_dir, 'toweros-host-*.xz'))
    if not host_images:
        logger.info("Host image not found in builds directory. Building a new image.")
        rpi_image_path = buildhost.build_image(builds_dir)
    else:
        rpi_image_path = host_images.pop()
        logger.info(f"Using host image {rpi_image_path}")
    return rpi_image_path

@clitask("Downloading pip packages...")
def prepare_pip_packages(builds_dir):
    os.makedirs(wd('dist/pip-packages'))
    tower_tools_wheel_path = TOWER_TOOLS_URL
    wheels = glob.glob(os.path.join(builds_dir, 'tower_tools-*.whl'))
    if wheels:
        wheel = wheels.pop()
        tower_tools_wheel_path = f"file://{wheel}"
        shutil.copy(wheel, wd('dist/pip-packages'))
    pip(
        "download", f"tower-tools @ {tower_tools_wheel_path or TOWER_TOOLS_URL}", 
        '-d', wd('dist/pip-packages'),
        _err_to_out=True, _out=logger.debug
    )

def prepare_installer():
    shutil.copytree(os.path.join(INSTALLER_DIR, 'installer'), wd('dist/installer'))

def prepare_docs():
    os.makedirs(wd('dist/docs'))
    shutil.copy(os.path.join(HOME_PATH, 'README.md'), wd('dist/docs'))
    shutil.copy(os.path.join(HOME_PATH, 'docs', 'Tower Whitepaper.pdf'), wd('dist/docs'))

def prepare_host_image(builds_dir):
    os.makedirs(wd('dist/builds'))
    host_image_path = find_host_image(builds_dir)
    shutil.copy(host_image_path, wd('dist/builds'))

@clitask("Building apk...")
def build_apk():
    shutil.copy(os.path.join(INSTALLER_DIR, 'APKBUILD'), wd('dist'))
    abuild(
        '-r', '-P', wd('apk-packages'), 
        _cwd=wd('dist'),
        _err_to_out=True, _out=logger.debug
    )

@clitask("Building image, be patient...")
def prepare_image(builds_dir):
    git('clone', '--depth=1', 'https://gitlab.alpinelinux.org/alpine/aports.git', _cwd=WORKING_DIR)
    shutil.copy(os.path.join(INSTALLER_DIR, 'mkimg.tower.sh'), wd('aports/scripts'))
    shutil.copy(os.path.join(INSTALLER_DIR, 'genapkovl-tower.sh'), wd('aports/scripts'))
    tower_repo = wd(f"apk-packages/{WORKING_DIR_NAME}")
    Command('sh')(
        wd('aports/scripts/mkimage.sh'),
        '--outdir', WORKING_DIR,
        '--repository', 'http://dl-cdn.alpinelinux.org/alpine/edge/main',
        '--repository', 'http://dl-cdn.alpinelinux.org/alpine/edge/community',
        '--repository', 'http://dl-cdn.alpinelinux.org/alpine/edge/testing',
        '--repository', f'file://{tower_repo}',
        '--profile', 'tower',
        '--tag', __version__,
         _err_to_out=True, _out=logger.debug,
         _cwd=WORKING_DIR
    )
    image_src_path = wd(f"alpine-tower-{__version__}-x86_64.iso")
    image_dest_path = os.path.join(
        builds_dir, 
        datetime.now().strftime(f'toweros-thinclient-{__version__}-%Y%m%d%H%M%S-x86_64.iso')
    )
    shutil.copy(image_src_path, image_dest_path)
    logger.info(f"Image built: {image_dest_path}")

@clitask("Building TowserOS-ThinClient image...", timer_message="TowserOS-ThinClient image built in {0}.")
def build_image(builds_dir):
    try:
        prepare_working_dir()
        prepare_pip_packages(builds_dir)
        prepare_installer()
        prepare_docs()
        # prepare_host_image(builds_dir) # TODO
        build_apk()
        prepare_image(builds_dir)
    finally:
        cleanup()
