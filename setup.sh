#!/bin/bash

# Create edid-rw directory in edid-emulator-webapp
sudo mkdir -p /edid-emulator-webapp/edid-rw

# Change into the edid-rw directory
cd /edid-emulator-webapp/edid-rw

# Install prerequisites
sudo apt-get install python3-smbus edid-decode

# Clone the edid-rw repository
sudo git clone https://github.com/bulletmark/edid-rw

# Change into the edid-rw directory
cd edid-rw

# Read and display EDID information
sudo./edid-rw 2 | edid-decode