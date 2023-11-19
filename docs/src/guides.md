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
        
        [thinclient]$ ssh -t storage restic -r /home/tower/backup init
        [thinclient]$ ssh -t office restic -r /home/tower/backup init \
                                           --from-repo sftp:storage:/home/tower/backup \
                                           --copy-chunker-params

    Note: `--copy-chunker-params` is important to ensure deduplication. 
    See "[Copying snapshots between repositories](https://restic.readthedocs.io/en/latest/045_working_with_repos.html#copying-snapshots-between-repositories)" for more options.

1. Backup `office`

        [thinclient]$ ssh -t office restic -r /home/tower/backup backup /home/tower/mydata

1. Copy `office` snapshot into `storage` repo

        [thinclient]$ restic -r sftp:storage:/home/tower/backup copy \
                             --from-repo sftp:office:/home/tower/backup \
                             latest

    Note: here `restic` copies the backup from the `office` host to the Thin Client, and then copies it to the `storage` host. You can optionally clear the cache stored on the Thin Client:
        
        [thinclient]$ rm -rf ~/.cache/restic

1. Restore backup into `office`

        [thinclient]$ restic -r sftp:office:/home/tower/backup copy \
                             --from-repo sftp:storage:/home/tower/backup \
                             latest --host office
        [thinclient]$ ssh -t office restic -r /home/tower/backup restore latest --target /


## Install `pip` package in offline host using online host

1. Install `pip` in online and offline host

        [thinclient]$ tower install router python3 py3-pip
        [thinclient]$ tower install office python3 py3-pip

1. Download package and dependencies in online host

        [thinclient]$ ssh router mkdir mypackages
        [thinclient]$ ssh router pip download <package_name> -d mypackages 

1. Copy package and dependencies to offline host

        [thinclient]$ scp -r router:mypackages office:

1. Install `pip` package in offline host

        [thinclient]$ ssh office pip install --no-index --find-links="~/mypackages" <package_name>

1. Clean cache in online and offline host

        [thinclient]$ ssh office rm -rf mypackages
        [thinclient]$ ssh router rm -rf mypackages