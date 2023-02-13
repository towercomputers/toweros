import configparser
import logging
import time
import os

import sh
from sh import Command

logger = logging.getLogger('tower')

def disable_rpi_image_ejection():
    conf_path = os.path.join(os.path.expanduser('~'), '.config/', 'Raspberry Pi/', 'Imager.conf')
    conf_dir = os.path.dirname(conf_path)
    config = configparser.ConfigParser()
    if os.path.exists(conf_path):
        config.read(conf_path)
    config[configparser.DEFAULTSECT]['eject'] = 'false'
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)
    with open(conf_path, 'w') as f:
        config.write(f)

def dd(image, device):
    if get_mount_point(device) is not None:
        unmount(device)
    dd(f"if={image}",f"of={device}", "bs=8m", "oflag=sync")

def write_image(image, device):
    rpi_imager_path = "/usr/bin/rpi-imager"
    start_time = time.time()
    if os.path.exists(rpi_imager_path):
        disable_rpi_image_ejection()
        rpi_imager = Command(rpi_imager_path)
        logger.info(f"Burning {device} with rpi-imager, be patient please...")
        with sh.contrib.sudo(password="", _with=True):
            rpi_imager('--cli', '--debug', image, device, _out=logger.debug)
    else:
        logger.info(f"Burning {device} with dd, be patient please...")
        dd(image, device)
    duration = time.time() - start_time
    logger.info(f"{device} burnt in {duration}s.")


