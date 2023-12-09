import os
import logging
import glob

from towerlib.utils.shell import shasum, mkdir
from towerlib.utils import network
from towerlib.utils.shell import sh_sudo
from towerlib.utils.decorators import clitask
from towerlib.utils.exceptions import InvalidChecksum

logger = logging.getLogger('tower')

REQUIRED_BUILDS = {
    "alpine-rpi": {
        "filename": "alpine-rpi-3.19.0-aarch64.tar.gz",
        "url": "https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/aarch64/alpine-rpi-3.19.0-aarch64.tar.gz",
        "checksum": "5621e7e597c3242605cd403a0a9109ec562892a6c8a185852b6b02ff88f5503c",
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
        with sh_sudo(password="", _with=True): # nosec B106
            mkdir('-p', builds_dir)
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
        logger.info('%s not found in builds directory.', build["filename"])
        network.download_file(build["url"], file_path)
    chek_sha_sum(file_path, build["checksum"])
    return file_path

def find_host_image():
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
                    return compressed_host_images.pop()
                return uncompressed_host_images.pop()
            if compressed_host_images:
                return compressed_host_images.pop()
            if uncompressed_host_images:
                return uncompressed_host_images.pop()
    return None
