#!/bin/bash

set -e
set -x

GIT_NAME="$1"
GIT_EMAIL="$2"
GIT_KEY_PATH="$3"
USAGE="Usage: $0 <git_name> <git_email> <git_key_path>"

if [ -d ~/towercomputers/toweros ]; then
  echo "~/towercomputers/toweros directory exists: skipping git configuration."
fi

# update Git configuration
if [ ! -z "$GIT_NAME" ]; then
    git config --global user.name "$GIT_NAME"
else
    echo "$USAGE"
    exit 1
fi

if [ ! -z "$GIT_EMAIL" ]; then
    git config --global user.email "$GIT_EMAIL"
else
    echo "$USAGE"
    exit 1
fi

# download toweros sources
if [ ! -z "$GIT_KEY_PATH" ]; then
    mkdir -p ~/.ssh
    cp $GIT_KEY_PATH ~/.ssh
    KEY_NAME=$(basename $GIT_KEY_PATH)
    touch ~/.ssh/config
    echo "Host github.com" >> ~/.ssh/config
    echo "  HostName github.com" >> ~/.ssh/config
    echo "  IdentityFile ~/.ssh/$KEY_NAME" >> ~/.ssh/config
    echo "  User git" >> ~/.ssh/config
    GITHUB_KEY="github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk="
    touch ~/.ssh/known_hosts
    echo "$GITHUB_KEY" >> ~/.ssh/known_hosts
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/*
    mkdir -p ~/towercomputers
    cd ~/towercomputers
    git clone git@github.com:towercomputers/toweros.git
else
    echo "$USAGE"
    exit 1
fi
