import os
import logging
import glob

from sh import shasum

from tower.utils import network
from tower.utils.decorators import clitask

logger = logging.getLogger('tower')

class InvalidChecksum(Exception):
    pass

REQUIRED_BUILDS = {
    "arch-linux-arm": {
        "filename": "ArchLinuxARM-rpi-armv7-latest.tar.gz",
        "url": "http://os.archlinuxarm.org/os/ArchLinuxARM-rpi-armv7-latest.tar.gz",
        "checksum": "65472324ff51bde690379c67b7c5e299e532e63747bf1f71d20552c63708e1b0"
    },
}

def init_builds_dir(args_builds_dir):
    builds_dir = args_builds_dir
    # if not provided check if builds is in ./ or in ~/.cache/tower/
    if not builds_dir:
        builds_dir = os.path.join(os.getcwd(), 'dist')
        if os.path.isdir(builds_dir):
            return builds_dir
        builds_dir = os.path.join(os.getcwd(), 'builds')
        if os.path.isdir(builds_dir):
            return builds_dir
        builds_dir = os.path.join(os.path.expanduser('~'), '.cache', 'tower', 'builds')
        if os.path.isdir(builds_dir):
            return builds_dir
    # if not exists, create it
    if not os.path.isdir(builds_dir):
        os.makedirs(builds_dir)
    return builds_dir

def sha_sum(file_path):
    res = shasum('-a256', file_path)
    return res.split(" ")[0].strip()

@clitask("Checking {0} checksum...")
def chek_sha_sum(file_path, checksum):
    file_checksum = sha_sum(file_path)
    if file_checksum != checksum:
        raise InvalidChecksum(f"Invalid checksum for {file_path}: {checksum} != {file_checksum}")

def prepare_required_build(build_name, builds_dir):
    build = REQUIRED_BUILDS[build_name]
    file_path = os.path.join(builds_dir, build["filename"])
    if not os.path.isfile(file_path):
        logger.info(f'{build["filename"]} not found in builds directory.')
        network.download_file(build["url"], file_path)
    chek_sha_sum(file_path, build["checksum"])
    return file_path

def find_host_image():
    image_path = None
    builds_dirs = [
        os.path.join(os.getcwd(), 'dist'),
        os.path.join(os.getcwd(), 'builds'),
        os.path.join(os.path.expanduser('~'), '.cache', 'tower', 'builds')
    ]
    for builds_dir in builds_dirs:
        if os.path.isdir(builds_dir):
            host_images = glob.glob(os.path.join(builds_dir, 'toweros-host-*.xz'))
            host_images += glob.glob(os.path.join(builds_dir, 'toweros-host-*.img'))
            if host_images:
                image_path = host_images.pop()
                break
    return image_path
