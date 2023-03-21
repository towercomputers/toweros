# On amd64:
#  
# Build docker image with:
# docker build -t build-tower-image:latest .
#
# Build TowerOS image with
# docker run --name towerbuilder --user tower \
#       -v /var/run/docker.sock:/var/run/docker.sock --privileged build-tower-image thinclient
# docker cp towerbuilder:/home/tower/toweros-20230318154719-x86_64.iso ./
#
# Build hosts image with
# docker run --name towerbuilder --user tower -v /var/run/docker.sock:/var/run/docker.sock build-tower-image host
# docker cp towerbuilder:/home/tower/Raspbian-tower-20230321173402.img.xz ./
#
# On Apple M1 (arm64):
#
# docker buildx create --use
# docker buildx build -t build-tower-image:latest --platform=linux/amd64 --output type=docker .
# docker run --privileged --rm tonistiigi/binfmt --install all
# docker run --platform=linux/amd64 --name towerbuilder --user tower \
#       -v /var/run/docker.sock:/var/run/docker.sock --privileged build-tower-image thinclient
# docker cp towerbuilder:/home/tower/toweros-20230318154719-x86_64.iso ./
#

FROM archlinux:latest

ARG TOWER_WHEEL_PATH="dist/tower_tools-0.0.1-py3-none-any.whl"

# install pacman packages
RUN pacman -Suy --noconfirm 
RUN pacman -S --noconfirm openssh git python python-pip avahi iw wireless_tools base-devel docker archiso

# create `tower` user
RUN useradd -m tower -p $(echo $tower | openssl passwd -1 -stdin)
RUN echo "tower ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
RUN usermod -aG docker tower
ENV PATH="$PATH:/home/tower/.local/bin"

# change default user
USER tower
WORKDIR /home/tower 

# install pip dependencies
RUN python -m pip install --upgrade pip
RUN pip install gevent python-xlib requests sh backports.pbkdf2 passlib sshconf hatchling wheel \
        "x2go @ https://code.x2go.org/releases/source/python-x2go/python-x2go-0.6.1.3.tar.gz"

# copy and install `tower-tools` at the end so everything above is cached
COPY --chown=tower:tower $TOWER_WHEEL_PATH ./
RUN pip install $(basename $TOWER_WHEEL_PATH)

ENTRYPOINT ["build-tower-image", \
            "--tower-tools-wheel-path", "file:///home/tower/tower_tools-0.0.1-py3-none-any.whl"]