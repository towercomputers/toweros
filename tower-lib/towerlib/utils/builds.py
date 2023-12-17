import os
import logging
import glob

from towerlib.utils.shell import shasum
from towerlib.utils import network
from towerlib.utils.decorators import clitask
from towerlib.utils.exceptions import InvalidChecksum
from towerlib import config

logger = logging.getLogger('tower')

def sha_sum(file_path):
    res = shasum('-a256', file_path)
    return res.split(" ")[0].strip()

@clitask("Checking {0} checksum...")
def chek_sha_sum(file_path, checksum):
    file_checksum = sha_sum(file_path)
    if file_checksum != checksum:
        raise InvalidChecksum(f"Invalid checksum for {file_path}: {checksum} != {file_checksum}")

def download_alpine_rpi():
    build_filename = os.path.basename(config.ALPINE_RPI_URL)
    build_path = os.path.join(config.TOWER_BUILDS_DIR, build_filename)
    if not os.path.isfile(build_path):
        logger.info('%s not found in builds directory.', build_filename)
        network.download_file(config.ALPINE_RPI_URL, build_path)
    chek_sha_sum(build_path, config.ALPINE_RPI_CHECKSUM)
    return build_path

def find_host_image():
    if os.path.isdir(config.TOWER_BUILDS_DIR):
        compressed_host_images = glob.glob(os.path.join(config.TOWER_BUILDS_DIR, 'toweros-host-*.img'))
        compressed_host_images.sort()
        uncompressed_host_images = glob.glob(os.path.join(config.TOWER_BUILDS_DIR, 'toweros-host-*.xz'))
        uncompressed_host_images.sort()
        if compressed_host_images and uncompressed_host_images:
            compressed_name = os.path.basename(compressed_host_images[-1]).replace('.img.xz', '')
            uncompressed_name = os.path.basename(uncompressed_host_images[-1]).replace('.img', '')
            if compressed_name > uncompressed_name:
                return compressed_host_images.pop()
            return uncompressed_host_images.pop()
        if compressed_host_images:
            return compressed_host_images.pop()
        if uncompressed_host_images:
            return uncompressed_host_images.pop()
    return None
