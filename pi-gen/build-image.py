#!/usr/bin/env python3

import argparse
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time

from sh import git, docker, Command

GIT_BRANCH = "arm64"

def build_image():
    start_time = time.time()

    config = dict(
        IMG_NAME='Raspbian',
        DEPLOY_COMPRESSION='xz',
        FIRST_USER_NAME='tower',
        FIRST_USER_PASS='tower',
        ENABLE_SSH=1,
        DISABLE_FIRST_BOOT_USER_RENAME=1,
        STAGE_LIST='stage0 stage1 stage2 stagetower'
    )

    working_dir = tempfile.gettempdir()
    git_folder = os.path.join(working_dir, 'pi-gen')
    config_path = os.path.join(git_folder, 'config')
    patch_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tower-distribution.patch')
    build_docker_path = os.path.join(git_folder, 'build-docker.sh')
    image_src_path = os.path.join(git_folder, 'deploy', datetime.now().strftime('image_%Y-%m-%d-Raspbian-tower.img.xz'))
    image_dest_path = os.path.join(os.getcwd(), datetime.now().strftime('Raspbian-tower-%Y%m%d%H%M%S.img.xz'))

    if os.path.exists(git_folder):
        shutil.rmtree(git_folder)

    logger.info("Cloning `pi-gen` repository...")
    git("clone", "--branch", GIT_BRANCH, "https://github.com/RPI-Distro/pi-gen.git", _cwd=working_dir, _out=logger.debug)

    logger.info("Apply `tower` distribution patch...")
    git("apply", patch_path, _cwd=git_folder, _out=logger.debug)
    Path(os.path.join(git_folder, 'stage2', 'SKIP_IMAGES')).touch()
    with open(config_path, "w") as f:
        f.write("\n".join([f'{key}="{value}"' for key, value in config.items()]))

    logger.info("Build image with docker, please be patient...")
    try:
        Command(build_docker_path)(_cwd=git_folder, _out=logger.debug)
    except KeyboardInterrupt:
        logger.info("Build interrupted. Cleaning docker container and files, please wait some seconds..")
        shutil.rmtree(git_folder)
        docker("stop", "-t", "5", "pigen_work")
        docker("rm", "-v", "pigen_work")
        exit()

    shutil.move(image_src_path, image_dest_path)

    logger.info("Cleaning files...")
    shutil.rmtree(git_folder)

    duration = timedelta(seconds=time.time() - start_time)
    logger.info(f"Image `{image_dest_path}` created in {duration}.")
    

parser = argparse.ArgumentParser(description="""Generate Raspberry Pi OS compatible with `tower`""")
parser.add_argument(
    '-v', '--verbose',
    help="""Set log level to DEBUG.""",
    required=False,
    action='store_true',
    default=False
)
args = parser.parse_args()

logger = logging.getLogger('tower')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG if args.verbose else logging.INFO)
logger.addHandler(console_handler)

build_image()


