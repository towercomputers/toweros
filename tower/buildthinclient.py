from datetime import datetime
import logging
import os
import glob
import getpass
import re

from sh import pacman, rm, cp, repo_add, pip, mkarchiso, chown, bsdtar, Command, mkdir

from tower import buildhost, utils
from tower.utils import clitask
from tower.__about__ import __version__

logger = logging.getLogger('tower')

TOWER_TOOLS_URL = "git+ssh://github.com/towercomputing/tools.git"

WORKING_DIR = os.path.join(os.path.expanduser('~'), 'build-toweros-thinclient-work')
INSTALLER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'toweros-thinclient')

def wd(path):
    return os.path.join(WORKING_DIR, path)

def prepare_working_dir():
    if os.path.exists(WORKING_DIR):
        raise Exception(f"f{WORKING_DIR} already exists! Is another build in progress? if not, delete this folder and try again.")
    os.makedirs(WORKING_DIR)
    os.makedirs(wd('blankdb'))

@clitask("Cleaning up...")
def cleanup():
    rm('-rf', WORKING_DIR, _out=logger.debug)

def find_host_image(builds_dir):
    host_images = glob.glob(os.path.join(builds_dir, 'toweros-host-*.xz'))
    if not host_images:
        logger.info("Host image not found in builds directory. Building a new image.")
        rpi_image_path = buildhost.build_image(builds_dir)
    else:
        rpi_image_path = host_images.pop()
        logger.info(f"Using host image {rpi_image_path}")
    return rpi_image_path

def find_tower_tools(builds_dir):
    wheels = glob.glob(os.path.join(builds_dir, 'tower_tools-*.whl'))
    tower_tools_wheel_path = f"file://{wheels.pop()}" if wheels else TOWER_TOOLS_URL
    return tower_tools_wheel_path

@clitask("Downloading pacman packages...")
def download_pacman_packages():
    with open(os.path.join(INSTALLER_DIR, 'files', 'packages.x86_64'), 'r') as fp:
        packages_str = fp.read()
        # remove nx packages
        packages = re.sub(r'\nnx[^\n]+', "", packages_str).split("\n")
    pacman('-Suy', _out=logger.debug)
    pacman('-Syw', '--cachedir', wd('pacman-packages'), '--dbpath', wd('blankdb'), '--noconfirm', *packages, _out=logger.debug)

@clitask("Preparing nx packages...")
def prepare_nx_packages(nx_tar_path):
    bsdtar('-xpf', nx_tar_path, '-C', WORKING_DIR, _out=logger.debug)
    nx_path = os.path.join(WORKING_DIR, 'nx-x86_64')
    nx_zst_path = os.path.join(nx_path, '*.zst')
    nx_packages = glob.glob(nx_zst_path)
    pacman('-Uw', '--cachedir', wd('pacman-packages'), '--dbpath', wd('blankdb'), '--noconfirm', *nx_packages, _out=logger.debug)
    for pkg in nx_packages:
        cp(pkg, wd('pacman-packages'))

@clitask("Preparing pacman database...")
def create_pacman_db():
    zsts = [f for f in glob.glob(f"{wd('pacman-packages')}/*") if f.split('.').pop() != 'sig']
    repo_add(os.path.join(wd('pacman-packages'), 'towerpackages.db.tar.gz'), *zsts, _out=logger.debug)

@clitask("Downloading pip packages...")
def download_pip_packages(tower_tools_wheel_path):
    pip("download", f"tower-tools @ {tower_tools_wheel_path or TOWER_TOOLS_URL}", '-d', wd('pip-packages'), _out=logger.debug)

@clitask("Preparing archiso folder..")
def prepare_archiso(builds_dir, rpi_image_path):
    # copy installer, pacman and pip packages
    cp('-r', '/usr/share/archiso/configs/releng/', wd('archiso'))
    root_path = os.path.join(wd('archiso'), 'airootfs', 'root')
    installer_files = glob.glob(os.path.join(INSTALLER_DIR, '*.sh'))
    installer_files += glob.glob(os.path.join(INSTALLER_DIR, 'files', '*'))
    for f in installer_files:
        cp(f, root_path)
    cp('-r', wd('pacman-packages'), root_path)
    cp('-r', wd('pip-packages'), root_path)
    cp(os.path.join(INSTALLER_DIR, 'files', 'grub.cfg'), os.path.join(wd('archiso'), 'grub'))
    # add packages needed by the installer
    package_list = os.path.join(wd('archiso'), 'packages.x86_64')
    add_packages = ["xorg-server", "xorg-xinit", "yad"]
    for pkg in add_packages:
        Command('sh')('-c', f'echo "{pkg}" >>  {package_list}')
    # start installer on login
    zlogin = os.path.join(wd('archiso'), 'airootfs', 'root', '.zlogin')
    Command('sh')('-c', f'echo "sh ~/00_install_toweros_thinclient.sh" >>  {zlogin}')
    # prepare builds dir
    builds_path = os.path.join(root_path, 'builds')
    mkdir('-p', builds_path)
    cp(rpi_image_path, builds_path)
    cp(os.path.join(builds_dir, 'nx-x86_64.tar.gz'), builds_path)
    cp(os.path.join(builds_dir, 'nx-armv7h.tar.gz'), builds_path)
    wheels = glob.glob(os.path.join(builds_dir, 'tower_tools-*.whl'))
    if wheels:
        cp(wheels.pop(), builds_path)

@clitask("Building image file with mkarchiso...")
def make_archiso(builds_dir):
    archiso_out_path = os.path.join(WORKING_DIR, 'out')
    image_src_path = os.path.join(archiso_out_path, datetime.now().strftime('archlinux-%Y.%m.%d-x86_64.iso'))
    image_dest_path = os.path.join(builds_dir, datetime.now().strftime(f'toweros-thinclient-{__version__}-%Y%m%d%H%M%S-x86_64.iso'))
    mkarchiso('-v', wd('archiso'), _cwd=WORKING_DIR, _out=logger.debug)
    cp(image_src_path, image_dest_path)
    owner = getpass.getuser()
    chown(f"{owner}:{owner}", image_dest_path)
    logger.info(f"Image ready: {image_dest_path}")
    return image_dest_path

@clitask("Building TowserOS-ThinClient image...", timer_message="TowserOS-ThinClient image built in {0}.", sudo=True)
def build_image(builds_dir):
    try:
        prepare_working_dir()
        # prepare required builds
        tower_tools_wheel_path = find_tower_tools(builds_dir)
        nx_tar_path = utils.prepare_required_build("nx-x86_64", builds_dir)
        nx_arm_tar_path = utils.prepare_required_build("nx-armv7h", builds_dir)
        rpi_image_path = find_host_image(builds_dir)
        # create pacman cache
        download_pacman_packages()
        prepare_nx_packages(nx_tar_path)
        create_pacman_db()
        # create pip cache
        download_pip_packages(tower_tools_wheel_path)
        # prepare and run archiso
        prepare_archiso(builds_dir, rpi_image_path)
        make_archiso(builds_dir)
    finally:
        cleanup()
