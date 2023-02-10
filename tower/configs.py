DEFAULT_OS_IMAGE = "https://downloads.raspberrypi.org/raspios_arm64/images/raspios_arm64-2022-09-26/2022-09-22-raspios-bullseye-arm64.img.xz"
DEFAULT_SSH_USER = "tower"
DEFAULT_SSH_PORT = 22

class MissingConfigValue(Exception):
    pass

def check_missing_value(key, value):
    if not value:
        raise MissingConfigValue(f"Impossible to determine the {key}. Please use the option --{key}.")
