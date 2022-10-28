#!/usr/bin/with-contenv bashio

echo "Starting..."

python3 -m pip install /data/requirements.txt

echo "Done installation of requirements, running..."

python3 /data/main.py