#!/usr/bin/with-contenv bashio

echo "Starting..."

python3 -m pip install /app/requirements.txt

echo "Done installation of requirements, running..."

python3 /app/main.py