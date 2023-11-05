FROM alpine:3.18

# docker build -f ./Dockerfile ../

# hatch build -t wheel
ARG TOWER_LIB_WHEEL_PATH="tower-lib/dist/tower_lib-0.1.3-py3-none-any.whl"
ARG TOWER_CLI_WHEEL_PATH="tower-cli/dist/tower_cli-0.1.3-py3-none-any.whl"

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

# copy toweros repo
RUN mkdir -p /home/tower/toweros
COPY --chown=tower:tower ./tower-build-cli /home/tower/toweros/tower-build-cli
COPY --chown=tower:tower ./tower-lib /home/tower/toweros/tower-lib
COPY --chown=tower:tower ./tower-cli /home/tower/toweros/tower-cli
COPY --chown=tower:tower ./docs /home/tower/toweros/docs
COPY --chown=tower:tower ./README.md /home/tower/toweros/README.md

# install tower-lib
WORKDIR /home/tower/toweros/tower-build-cli/
RUN pip install -e ../tower-lib

ENTRYPOINT ["./tower-build"]