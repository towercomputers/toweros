FROM alpine:3.18

# hatch build -t wheel
ARG TOWER_WHEEL_PATH="dist/tower_tools-0.0.1-py3-none-any.whl"

# install apk packages
RUN apk update 
RUN apk add alpine-base coreutils python3 py3-pip rsync git lsblk perl-utils xz \
      e2fsprogs-extra parted musl-locales sudo openssh \ 
      alpine-sdk build-base apk-tools acct acct-openrc alpine-conf sfdisk busybox \
      fakeroot syslinux xorriso squashfs-tools mtools dosfstools grub-efi abuild \
      agetty runuser nano vim net-tools losetup

# create `tower` user
RUN adduser -D tower tower
# add user to abuild group (necessary for building packages)
RUN addgroup tower abuild
# add `tower` user to sudoers
RUN mkdir -p /etc/sudoers.d
RUN echo "tower ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
# update path
ENV PATH="$PATH:/home/tower/.local/bin"

# change default user
USER tower
WORKDIR /home/tower

# generate abuild keys
RUN abuild-keygen -a -i -n

# copy and install `tower-tools` at the end so everything above is cached
RUN mkdir -p /home/tower/.cache/tower/builds
COPY --chown=tower:tower $TOWER_WHEEL_PATH /home/tower/.cache/tower/builds/
RUN pip install /home/tower/.cache/tower/builds/$(basename $TOWER_WHEEL_PATH)

ENTRYPOINT ["build-tower-image"]