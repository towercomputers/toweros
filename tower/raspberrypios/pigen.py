from datetime import datetime, timedelta
import logging
import os
import sys
from pathlib import Path
import shutil
import tempfile
import time
from io import StringIO
import json

from sh import git, docker, Command

GIT_BRANCH = "arm64"

logger = logging.getLogger('tower')

def build_image():
    start_time = time.time()

    config = dict(
        IMG_NAME='Raspbian',
        DEPLOY_COMPRESSION='xz',
        STAGE_LIST='stage0 stage1 stage2 stagetower'
    )

    working_dir = tempfile.gettempdir()
    git_folder = os.path.join(working_dir, 'pi-gen')
    config_path = os.path.join(git_folder, 'config')
    installer_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'installer')
    build_docker_path = os.path.join(git_folder, 'build-docker.sh')
    boot_folder = os.path.join(git_folder, 'stage1', '00-boot-files', 'files')
    image_src_path = os.path.join(git_folder, 'deploy', datetime.now().strftime('image_%Y-%m-%d-Raspbian-tower.img.xz'))
    image_dest_path = os.path.join(os.getcwd(), datetime.now().strftime('Raspbian-tower-%Y%m%d%H%M%S.img.xz'))

    if os.path.exists(git_folder):
        shutil.rmtree(git_folder)

    logger.info("Cloning `pi-gen` repository...")
    git("clone", "--branch", GIT_BRANCH, "https://github.com/RPI-Distro/pi-gen.git", _cwd=working_dir, _out=logger.debug)

    logger.info("Apply `tower` distribution patch...")
    git("apply", os.path.join(installer_path, 'tower-distribution.patch'), _cwd=git_folder, _out=logger.debug)
    Path(os.path.join(git_folder, 'stage2', 'SKIP_IMAGES')).touch()
    with open(config_path, "w") as f:
        f.write("\n".join([f'{key}="{value}"' for key, value in config.items()]))
    shutil.copy(os.path.join(installer_path, 'firstrun.sh'), boot_folder)
    shutil.copy(os.path.join(installer_path, 'configure_firewall.sh'), boot_folder)

    logger.info("Build image with docker, please be patient...")
    try:
        buf = StringIO()
        docker('info', '-f', '{{json .Architecture}}', _out=buf)
        arch = json.loads(buf.getvalue())
        if arch not in ["aarch64", "arm64"]:
            docker('run', '--rm', '--privileged', 'multiarch/qemu-user-static', '--reset', '-p', 'yes', _out=logger.debug)
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

    return image_dest_path
