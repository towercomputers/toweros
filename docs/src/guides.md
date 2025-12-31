## Move a file from one host to another

        [thinclient]$ scp -r router:/home/tower/myfile office:/home/tower
        [thinclient]$ ssh router rm /home/tower/myfile


## Backup hosts with `restic`

It is recommended to reserve one of your hosts, for example `storage`, to store the backups of all the other hosts there. Here's how, using `restic`, you can store the backup of an `office` host on a `storage` host:

1. Install restic

        [thinclient]$ tower install storage restic
        [thinclient]$ tower install office restic
        [thinclient]$ tower install thinclient restic

1. Initialize restic repo in each host
        
        [thinclient]$ restic -r sftp:storage:backup init
        [thinclient]$ restic -r sftp:office:backup init --from-repo sftp:storage:backup --copy-chunker-params

    Note: `--copy-chunker-params` is important to ensure deduplication. 
    See "[Copying snapshots between repositories](https://restic.readthedocs.io/en/latest/045_working_with_repos.html#copying-snapshots-between-repositories)" for more options.

1. Backup `~/mydata` folder in `office` host

        [thinclient]$ ssh -t office restic -r backup backup mydata

1. Copy `office` snapshot into `storage` repo

        [thinclient]$ restic -r sftp:storage:backup copy --from-repo sftp:office:backup latest

    Note: here `restic` copies the backup from the `office` host to the thin client, and then copies it to the `storage` host. You can optionally clear the cache stored on the thin client:
        
        [thinclient]$ rm -rf ~/.cache/restic

1. Restore backup into `office`

        [thinclient]$ restic -r sftp:office:backup copy --from-repo sftp:storage:backup latest --host office
        [thinclient]$ ssh -t office restic -r backup restore latest --target ~/


## Install `pip` package in offline host using online host

Before installing a package with `pip`, check that there is no `apk` package installable with `tower install`.

1. Install `pip` in online and offline host

        [thinclient]$ tower install web python3 py3-pip
        [thinclient]$ tower install office python3 py3-pip

1. Download package and dependencies in online host

        [thinclient]$ ssh web mkdir mypackages
        [thinclient]$ ssh web pip download <package_name> -d mypackages 

1. Copy package and dependencies to offline host

        [thinclient]$ scp -r web:mypackages office:

1. Install `pip` package in offline host

To install a package with `pip` you must create a virtual environment. Please refer to **[the official documentation](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)**.
Make sure to install your environment in the `/home` folder if you want it to be preserved during an upgrade.

        [thinclient]$ ssh office
        [office]$ mkdir myproject
        [office]$ cd myproject
        [office]$ python3 -m venv .venv
        [office]$ source .venv/bin/activate
        (.venv)[office]$ pip install --no-index --find-links="~/mypackages" <package_name>

1. Clean up

        [thinclient]$ ssh office rm -rf mypackages
        [thinclient]$ ssh web rm -rf mypackages

## Install `npm` package in offline host using online host

1. Install `npm` in online and offline host

        [thinclient]$ tower install web npm
        [thinclient]$ tower install office npm

1. Download package and dependencies in online host

        [thinclient]$ ssh web 'mkdir mypackages && cd mypackages && npm init -y'
        [thinclient]$ ssh web 'cd mypackages && npm install -B <package_name> && npm pack'

1. Copy package and dependencies to offline host

        [thinclient]$ scp -r web:mypackages/mypackages-1.0.0.tgz office:

1. Install `npm` package in offline host

        [thinclient]$ ssh office tar -xvzf mypackages-1.0.0.tgz
        [thinclient]$ ssh office 'sudo npm install -g package/node_modules/*/'

1. Clean up

        [thinclient]$ ssh office rm -rf mypackages-1.0.0.tgz package
        [thinclient]$ ssh web rm -rf mypackages
