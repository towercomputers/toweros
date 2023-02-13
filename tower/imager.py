import os
import sys
import shutil
import hashlib

from sh import xz
import requests

#from tower import osutils
#from tower import computers

def download_image(url, archive_hash):
    if not os.path.exists(".cache"):
        os.makedirs(".cache")

    xz_filename = f".cache/{url.split('/').pop()}"
    img_filename = xz_filename.replace(".xz", "")

    if not os.path.exists(img_filename):
        if not os.path.exists(xz_filename):
            print(f"Downloading {url}...")
            resp = requests.get(url)
            with open(xz_filename, "wb") as f:
                f.write(resp.content)

        print(f"Calculating sha256 hash...")
        sha256_hash = hashlib.sha256()
        with open(xz_filename, "rb") as f:
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
            xz_hash = sha256_hash.hexdigest()

        print(xz_hash, archive_hash)
        if xz_hash != archive_hash:
            sys.exit("Invalid image hash")
        
        print("Decompressing image...")
        xz('-d', xz_filename)
    else:
        print("Using image in cache.")

    print("Image ready to burn.")
    return img_filename


# TODO: all this files should be already in the image
def copy_firstrun_files(mountpoint):
    for filename in os.listdir('firstrun/'):
        shutil.copyfile(f'firstrun/{filename}', os.path.join(mountpoint, filename))


def set_firstrun_env(mountpoint, firstrun_env):
    env = "\n".join([f'{key}="{value}"' for key, value in firstrun_env.items()])
    with open(os.path.join(mountpoint, 'tower.env'), "w") as f:
        f.write(env)


def burn_image(image_url, image_hash, device, firstrun_env):
    image_path = download_image(image_url, image_hash)
    osutils.write_image(image_path, device)
    mountpoint = osutils.ensure_partition_is_mounted(device, 0) # first parition where to put files
    set_firstrun_env(mountpoint, firstrun_env)
    copy_firstrun_files(mountpoint)
    osutils.unmount_all(device)

