from datetime import datetime, timedelta
import logging
import os
import sys
from pathlib import Path
import shutil
import tempfile
import time
import glob
import getpass
import re

import sh
from sh import pacman, git, rm, cp, repo_add, makepkg, pip, mkarchiso, chown, bsdtar

from tower import towerospi

logger = logging.getLogger('tower')

TOWER_TOOLS_URL = "git+ssh://github.com/towercomputing/tools.git"

def clean_folders(folders):
    with sh.contrib.sudo(password="", _with=True):
        for folder in folders:
            rm('-rf', folder)

def download_pacman_packages(blankdb_path, towerpackages_path, installer_path):
    with open(os.path.join(installer_path, 'files', 'packages.x86_64'), 'r') as fp:
        packages_str = fp.read()
        # remove nx packages
        packages = re.sub(r'\nnx[^\n]+', "", packages_str).split("\n")
    with sh.contrib.sudo(password="", _with=True):
        pacman('-Suy', _out=logger.debug)
        pacman('-Syw', '--cachedir', towerpackages_path, '--dbpath', blankdb_path, '--noconfirm', *packages, _out=logger.debug)

def compile_nx_packages(working_dir, blankdb_path, towerpackages_path, nx_tar_path=None):
    if nx_tar_path:
        logger.info("Using NX build in builds directory.")
        bsdtar('-xpf', nx_tar_path, '-C', working_dir, _out=logger.debug)
        nx_path = os.path.join(working_dir, 'nx-x86_64')
        nx_zst_path = os.path.join(nx_path, '*.zst')
    else:
        logger.info("NX build not found. Build a new one. Be patient...")
        nx_path = os.path.join(working_dir, 'nx')
        nx_zst_path = os.path.join(nx_path, '*.zst')
        git("clone",  "https://aur.archlinux.org/nx.git", _cwd=working_dir, _out=logger.debug)
        makepkg('-c', '-s', '-r', '--noconfirm', _cwd=nx_path, _out=logger.debug)

    with sh.contrib.sudo(password="", _with=True):
        nx_packages = glob.glob(nx_zst_path)
        pacman('-Uw', '--cachedir', towerpackages_path, '--dbpath', blankdb_path, '--noconfirm', *nx_packages, _out=logger.debug)
        for pkg in nx_packages:
            cp(pkg, towerpackages_path)

def create_pacman_db(towerpackages_path):
    with sh.contrib.sudo(password="", _with=True):     
        zsts = [f for f in glob.glob(f'{towerpackages_path}/*') if f.split('.').pop() != 'sig']
        repo_add(os.path.join(towerpackages_path, 'towerpackages.db.tar.gz'), *zsts, _out=logger.debug)

def download_pip_packages(pippackages_path, tower_tools_wheel_path):
    pip("download", f"tower-tools @ {tower_tools_wheel_path or TOWER_TOOLS_URL}", '-d', pippackages_path, _out=logger.debug)

def prepare_archiso(archiso_path, installer_path, towerpackages_path, pippackages_path, rpi_image_path, builds_dir):
    # copy installer, pacman and pip packages
    cp('-r', '/usr/share/archiso/configs/releng/', archiso_path)
    root_path = os.path.join(archiso_path, 'airootfs', 'root')
    with sh.contrib.sudo(password="", _with=True):
        installer_files = glob.glob(os.path.join(installer_path, '*.sh'))
        installer_files += glob.glob(os.path.join(installer_path, 'files', '*'))
        for f in installer_files:
            cp(f, root_path)
        cp('-r', towerpackages_path, root_path)
        cp('-r', pippackages_path, root_path)
        cp(os.path.join(installer_path, 'files', 'grub.cfg'), os.path.join(archiso_path, 'grub'))
    # add packages
    with open(os.path.join(archiso_path, 'packages.x86_64'), "a") as f:
        f.write("xorg-server\n")
        f.write("xorg-xinit\n")
        f.write("yad\n")
    # start installer on login
    with open(os.path.join(archiso_path, 'airootfs', 'root', '.zlogin'), "w") as f:
        f.write("sh ~/00_install_toweros.sh\n")
    # prepare builds dir
    builds_path = os.path.join(root_path, 'builds')
    os.makedirs(builds_path)
    cp(rpi_image_path, builds_path)
    cp(os.path.join(builds_dir, 'nx-x86_64.tar.gz'), builds_path)
    cp(os.path.join(builds_dir, 'nx-armv7h.tar.gz'), builds_path)
    wheels = glob.glob(os.path.join(builds_dir, 'tower_tools-*.whl'))
    if wheels:
        cp(wheels.pop(), builds_path)

def make_archiso(archiso_path, working_dir, builds_dir):
    archiso_out_path = os.path.join(working_dir, 'out')
    image_src_path = os.path.join(archiso_out_path, datetime.now().strftime('archlinux-%Y.%m.%d-x86_64.iso'))
    image_dest_path = os.path.join(builds_dir, datetime.now().strftime('toweros-%Y%m%d%H%M%S-x86_64.iso'))
    with sh.contrib.sudo(password="", _with=True):
        mkarchiso('-v', archiso_path, _cwd=working_dir, _out=logger.debug)
        cp(image_src_path, image_dest_path)
        chown(getpass.getuser(), image_dest_path)
    return image_dest_path

def build_image(builds_dir):
    start_time = time.time()

    wheels = glob.glob(os.path.join(builds_dir, 'tower_tools-*.whl'))
    tower_tools_wheel_path = f"file://{wheels.pop()}" if wheels else TOWER_TOOLS_URL

    nx_tar_path = os.path.join(builds_dir, 'nx-x86_64.tar.gz')

    working_dir = os.path.join(os.getcwd(), datetime.now().strftime('buildtower%Y%m%d%H%M%S'))
    blankdb_path = os.path.join(working_dir, 'blankdb')
    towerpackages_path = os.path.join(working_dir, 'towerpackages')
    pippackages_path = os.path.join(working_dir, 'pippackages')
    archiso_path = os.path.join(working_dir, 'archtower')
    installer_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'toweros')

    clean_folders([working_dir])
    os.makedirs(blankdb_path)
    logger.info("Downloading pacman packages...")
    download_pacman_packages(blankdb_path, towerpackages_path, installer_path)
    logger.info("Prepare nx packages...")
    compile_nx_packages(working_dir, blankdb_path, towerpackages_path, nx_tar_path)
    logger.info("Preparing pacman database...")
    create_pacman_db(towerpackages_path)
    logger.info("Downloading pip packages...")
    download_pip_packages(pippackages_path, tower_tools_wheel_path)
    logger.info("Preparing host Rasperry PI OS image...")
    host_images = glob.glob(os.path.join(builds_dir, 'towerospi-*.xz'))
    if not host_images:
        logger.info("Host image not found in builds directory. Building a new image...")
        rpi_image_path = towerospi.build_image(builds_dir)
    else:
        rpi_image_path = host_images.pop()
        logger.info(f"Using host image found in builds directory: {rpi_image_path}")
    logger.info("Preparing archiso folder..")
    prepare_archiso(archiso_path, installer_path, towerpackages_path, pippackages_path, rpi_image_path, builds_dir)
    logger.info("Building image file...")
    image_dest_path = make_archiso(archiso_path, working_dir, builds_dir)
    clean_folders([working_dir])

    duration = timedelta(seconds=time.time() - start_time)
    logger.info(f"Image {image_dest_path} created in {duration}.")