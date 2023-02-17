#!/bin/bash

set +e

git clone --branch arm64 https://github.com/RPI-Distro/pi-gen.git
cp config pi-gen/
cd pi-gen
git apply ../tower-distribution.patch
./build-docker.sh
mv deploy/ ../../image
cd ..
rm -rf pi-gen/