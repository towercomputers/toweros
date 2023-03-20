# On Apple M1 (arm64):
#
# docker buildx create --use
# docker buildx build -t build-tower-image:latest --platform=linux/amd64 --output type=docker .
# docker run --privileged --rm tonistiigi/binfmt --install all
# docker run --platform=linux/amd64 --name towerbuilder --user tower --privileged build-tower-image
# docker cp towerbuilder:/home/tower/toweros-20230318154719-x86_64.iso ./
#
# On amd64:
#
# docker build -t build-tower-image:latest .
# docker run --name towerbuilder --user tower --privileged build-tower-image
# docker cp towerbuilder:/home/tower/toweros-20230318154719-x86_64.iso ./

FROM archlinux:latest

# install pacman packages
RUN pacman -Suy --noconfirm 
RUN pacman -S --noconfirm openssh git python python-pip avahi iw wireless_tools base-devel docker archiso

# create `tower` user
RUN useradd -m tower -p $(echo $tower | openssl passwd -1 -stdin)
RUN echo "tower ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/01_tower_nopasswd
ENV PATH="$PATH:/home/tower/.local/bin"

# change default user
USER tower
WORKDIR /home/tower 

# install pip dependencies
RUN python -m pip install --upgrade pip
RUN pip install gevent python-xlib requests sh backports.pbkdf2 passlib sshconf hatchling wheel \
        "x2go @ https://code.x2go.org/releases/source/python-x2go/python-x2go-0.6.1.3.tar.gz"

# copy Raspberry PI OS image
COPY dist/Raspbian-tower-latest.img.xz ./
RUN sudo chown tower:tower Raspbian-tower-latest.img.xz
# copy nx packages
COPY dist/nx ./nx
RUN sudo chown -R tower:tower nx/

# copy and install `tower-tools` at the end so everything above is cached
COPY dist/tower_tools-0.0.1-py3-none-any.whl ./
RUN sudo chown tower:tower tower_tools-0.0.1-py3-none-any.whl
RUN pip install tower_tools-0.0.1-py3-none-any.whl

ENTRYPOINT ["build-tower-image", "thinclient", \
            "--computer-image-path", "/home/tower/Raspbian-tower-latest.img.xz", \
            "--nx-path", "/home/tower/nx", \
            "--tower-tools-wheel-path", "file:///home/tower/tower_tools-0.0.1-py3-none-any.whl"]