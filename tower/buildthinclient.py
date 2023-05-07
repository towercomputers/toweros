from datetime import datetime
import logging
import os
import glob
import shutil
import sys

from sh import rm, git, pip, abuild, Command, apk, mkdir

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

def find_readme():
    readme_path = os.path.join(HOME_PATH, 'README.md')
    if os.path.exists(readme_path):
        return readme_path
    readme_path = os.path.join(HOME_PATH, 'docs', 'README.md')
    if os.path.exists(readme_path):
        return readme_path
    readme_path = "/var/towercomputers/docs/README.md"
    if os.path.exists(readme_path):
        return readme_path
    raise Exception("README.md not found!")

def check_abuild_key():
    abuild_folder = os.path.join(os.path.expanduser('~'), '.abuild')
    abuild_conf = os.path.join(abuild_folder, 'abuild.conf')
    if not os.path.exists(abuild_folder) or not os.path.exists(abuild_conf):
        logger.error("ERROR: You must have an abuild key to build the image. Please use `abuild-keygen -a -i`.")
        sys.exit()

@clitask("Downloading pip packages...")
def prepare_pip_packages(builds_dir):
    os.makedirs(wd('overlay/var/cache/pip-packages'))
    tower_tools_wheel_path = TOWER_TOOLS_URL
    wheels = glob.glob(os.path.join(builds_dir, 'tower_tools-*.whl'))
    if wheels:
        wheel = wheels.pop()
        tower_tools_wheel_path = f"file://{wheel}"
        shutil.copy(wheel, wd('overlay/var/cache/pip-packages'))
    pip(
        "download", f"tower-tools @ {tower_tools_wheel_path}", 
        '-d', wd('overlay/var/cache/pip-packages'),
        _err_to_out=True, _out=logger.debug
    )

def prepare_installer():
    os.makedirs(wd('overlay/var/towercomputers/'))
    shutil.copytree(os.path.join(INSTALLER_DIR, 'installer'), wd('overlay/var/towercomputers/installer'))

def prepare_docs():
    os.makedirs(wd('overlay/var/towercomputers/docs'))
    readme_path = find_readme()
    shutil.copy(readme_path, wd('overlay/var/towercomputers/docs'))
    shutil.copy(os.path.join(HOME_PATH, 'docs', 'Tower Whitepaper.pdf'), wd('overlay/var/towercomputers/docs'))

def prepare_build(builds_dir):
    os.makedirs(wd('overlay/var/towercomputers/builds'))
    host_image_path = find_host_image(builds_dir)
    shutil.copy(host_image_path, wd('overlay/var/towercomputers/builds'))
    wheels = glob.glob(os.path.join(wd('overlay/var/cache/pip-packages'), 'tower_tools-*.whl'))
    shutil.copy(wheels[0], wd('overlay/var/towercomputers/builds'))

def prepare_etc_folder():
    os.makedirs(wd('overlay/etc/apk/'))
    shutil.copy(os.path.join(INSTALLER_DIR, 'installer', 'files', 'world'), wd('overlay/etc/apk/'))
    os.chmod(wd('overlay/etc/apk/world'), 0o644)
    os.makedirs(wd('overlay/etc/profile.d'))
    shutil.copy(os.path.join(INSTALLER_DIR, 'installer', 'files', 'install.sh'), wd('overlay/etc/profile.d/'))
    os.chmod(wd('overlay/etc/profile.d/install.sh'), 0o755)
    shutil.copy(os.path.join(INSTALLER_DIR, 'installer', 'files', 'issue'), wd('overlay/etc/'))
    os.chmod(wd('overlay/etc/issue'), 0o644)
    shutil.copy(os.path.join(INSTALLER_DIR, 'installer', 'files', 'inittab'), wd('overlay/etc/'))
    os.chmod(wd('overlay/etc/inittab'), 0o644)

def prepare_overlay(builds_dir):
    prepare_pip_packages(builds_dir)
    prepare_installer()
    prepare_docs()
    prepare_etc_folder()
    prepare_build(builds_dir)

@clitask("Building image, be patient...")
def prepare_image(builds_dir):
    git('clone', '--depth=1', 'https://gitlab.alpinelinux.org/alpine/aports.git', _cwd=WORKING_DIR)
    shutil.copy(os.path.join(INSTALLER_DIR, 'mkimg.tower.sh'), wd('aports/scripts'))
    shutil.copy(os.path.join(INSTALLER_DIR, 'genapkovl-tower-thinclient.sh'), wd('aports/scripts'))
    shutil.copy(os.path.join(INSTALLER_DIR, 'installer', 'files', 'world'), wd('aports/scripts'))
    Command('sh')(
        wd('aports/scripts/mkimage.sh'),
        '--outdir', WORKING_DIR,
        '--repository', 'http://dl-cdn.alpinelinux.org/alpine/edge/main',
        '--repository', 'http://dl-cdn.alpinelinux.org/alpine/edge/community',
        '--repository', 'http://dl-cdn.alpinelinux.org/alpine/edge/testing',
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
        check_abuild_key()
        prepare_working_dir()
        prepare_overlay(builds_dir)
        prepare_image(builds_dir)
    finally:
        cleanup()
