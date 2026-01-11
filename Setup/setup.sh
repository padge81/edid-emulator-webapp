#!/bin/bash

echo "Starting setup..."

# Check for required commands
command -v python3 >/dev/null 2>&1 || { echo >&2 "Python3 is not installed. Aborting."; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo >&2 "pip3 is not installed. Aborting."; exit 1; }
command -v git >/dev/null 2>&1 || { echo >&2 "git is not installed. Aborting."; exit 1; }

# Change to the edid-emulator-webapp directory
cd./edid-emulator-webapp/

# Check if edid-rw repository is already cloned
if [! -d "edid-rw" ]; then
    echo "Cloning edid-rw repository..."
    git clone https://github.com/bulletmark/edid-rw
fi

# Change to the edid-rw directory
cd./edid-rw/

# Check if edid-rw can be run successfully
./edid-rw 2 | edid-decode >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "edid-rw successfully cloned and installed."
else
    echo "Error: edid-rw failed to install. Check the output above for more information."
fi