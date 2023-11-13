import os
import logging
import glob

from sh import shasum

from towerlib.utils import network
from towerlib.utils.decorators import clitask

logger = logging.getLogger('tower')

class InvalidChecksum(Exception):
    pass

REQUIRED_BUILDS = {
    "alpine-rpi": {
        "filename": "alpine-rpi-3.17.3-armv7.tar.gz",
        "url": "https://dl-cdn.alpinelinux.org/alpine/v3.17/releases/armv7/alpine-rpi-3.17.3-armv7.tar.gz",
        "checksum": "d623a05183164cc2280e6f934b2153761691ade62f67b03ec0b877d9f4ff6171"
    },
}

def init_builds_dir(args_builds_dir):
    builds_dir = args_builds_dir
    # if not provided check if builds is in ./ or in /var/towercomputers
    if not builds_dir:
        builds_dir = os.path.join(os.getcwd(), 'dist')
        if os.path.isdir(builds_dir):
            return builds_dir
        builds_dir = os.path.join(os.getcwd(), 'builds')
        if os.path.isdir(builds_dir):
            return builds_dir
        builds_dir = "/var/towercomputers/builds/"
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
        "/var/towercomputers/builds/"
    ]
    for builds_dir in builds_dirs:
        if os.path.isdir(builds_dir):
            compressed_host_images = glob.glob(os.path.join(builds_dir, 'toweros-host-*.img'))
            compressed_host_images.sort()
            uncompressed_host_images = glob.glob(os.path.join(builds_dir, 'toweros-host-*.xz'))
            uncompressed_host_images.sort()
            if compressed_host_images and uncompressed_host_images:
                compressed_name = os.path.basename(compressed_host_images[-1]).replace('.img.xz', '')
                uncompressed_name = os.path.basename(uncompressed_host_images[-1]).replace('.img', '')
                if compressed_name > uncompressed_name:
                    image_path = compressed_host_images.pop()
                    break
                else:
                    image_path = uncompressed_host_images.pop()
                    break
            elif compressed_host_images:
                image_path = compressed_host_images.pop()
                break
            elif uncompressed_host_images:
                image_path = uncompressed_host_images.pop()
                break
    return image_path
