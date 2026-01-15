#!/bin/bash
set -e

echo "=== Enabling Bluetooth PAN (Headless / Always Discoverable) ==="

# -------------------------------
# Packages
# -------------------------------
sudo apt update
sudo apt install -y \
    bluetooth \
    bluez \
    bluez-tools \
    bridge-utils \
    dnsmasq

# -------------------------------
# Enable Bluetooth service
# -------------------------------
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# -------------------------------
# Configure BlueZ (headless + PAN)
# -------------------------------
CONF="/etc/bluetooth/main.conf"

sudo sed -i 's/^#*EnableNetwork.*/EnableNetwork = true/' "$CONF"
sudo sed -i 's/^#*DiscoverableTimeout.*/DiscoverableTimeout = 0/' "$CONF"
sudo sed -i 's/^#*AutoEnable.*/AutoEnable = true/' "$CONF"

# Ensure ControllerMode exists and is dual
if ! grep -q "^ControllerMode" "$CONF"; then
    echo "ControllerMode = dual" | sudo tee -a "$CONF"
else
    sudo sed -i 's/^ControllerMode.*/ControllerMode = dual/' "$CONF"
fi

# Restart bluetooth to apply config
sudo systemctl restart bluetooth

# -------------------------------
# Create systemd service for PAN
# -------------------------------
SERVICE="/etc/systemd/system/bt-pan.service"

sudo tee "$SERVICE" > /dev/null <<'EOF'
[Unit]
Description=Bluetooth PAN (NAP)
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/bt-network -s nap
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable bt-pan.service
sudo systemctl restart bt-pan.service

# -------------------------------
# Network configuration (pan0)
# -------------------------------
sudo tee /etc/network/interfaces.d/bt-pan > /dev/null <<'EOF'
auto pan0
iface pan0 inet static
    address 192.168.44.1
    netmask 255.255.255.0
EOF

# -------------------------------
# DNS / DHCP for phone
# -------------------------------
DNSMASQ_CONF="/etc/dnsmasq.d/bt-pan.conf"

sudo tee "$DNSMASQ_CONF" > /dev/null <<'EOF'
interface=pan0
dhcp-range=192.168.44.10,192.168.44.50,255.255.255.0,12h
EOF

sudo systemctl restart dnsmasq

# -------------------------------
# Headless pairing + permanent discoverability
# -------------------------------
sudo bluetoothctl <<EOF
power on
agent NoInputNoOutput
default-agent
pairable on
discoverable on
exit
EOF

echo
echo "==========================================="
echo " Bluetooth PAN ENABLED (HEADLESS MODE)"
echo
echo " ✔ Always discoverable"
echo " ✔ No pairing confirmation required"
echo " ✔ PAN / NAP enabled"
echo
echo " Pair your phone via Bluetooth"
echo " Enable 'Network access / Internet sharing'"
echo
echo " Then open in browser:"
echo "   http://192.168.44.1:5000"
echo
echo " Works on Android & iOS"
echo "==========================================="
