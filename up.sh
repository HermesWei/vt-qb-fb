#!/bin/bash

sudo apt-get update
if ! command -v pip3 &> /dev/null; then apt-get install -y python3-pip; fi
pip install Flask requests

sudo apt install -y ffmpeg mediainfo pngquant

wget -P /root  https://github.com/lifujie25/lifj/raw/main/up.py

mkdir -p /home/pt

chmod a+x up.py

nohup python3 up.py &

grep -qxF 'nohup python3 /root/up.py &' /root/.bashrc || echo 'nohup python3 /root/up.py&' >> /root/.bashrc
