#!/bin/bash
set -e

echo "=== Enabling Bluetooth PAN (EDID Emulator) ==="

# Packages
sudo apt update
sudo apt install -y bluetooth bluez bluez-tools bridge-utils dnsmasq

# Enable bluetooth service
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# ---- Configure BlueZ for PAN ----
CONF="/etc/bluetooth/main.conf"

sudo sed -i 's/^#*EnableNetwork.*/EnableNetwork = true/' "$CONF"
sudo sed -i 's/^#*DiscoverableTimeout.*/DiscoverableTimeout = 0/' "$CONF"

# ---- Create systemd service ----
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

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable bt-pan.service
sudo systemctl restart bt-pan.service

# ---- Network configuration ----
# Create bt-pan interface config
sudo tee /etc/network/interfaces.d/bt-pan > /dev/null <<'EOF'
auto pan0
iface pan0 inet static
    address 192.168.44.1
    netmask 255.255.255.0
EOF

# ---- DNS / DHCP for phone ----
DNSMASQ_CONF="/etc/dnsmasq.d/bt-pan.conf"

sudo tee "$DNSMASQ_CONF" > /dev/null <<'EOF'
interface=pan0
dhcp-range=192.168.44.10,192.168.44.50,255.255.255.0,12h
EOF

sudo systemctl restart dnsmasq

# ---- Make device discoverable permanently ----
sudo bluetoothctl <<EOF
power on
discoverable on
pairable on
exit
EOF

echo
echo "==========================================="
echo " Bluetooth PAN ENABLED"
echo
echo " Pair your phone with the Pi"
echo " Enable 'Network access / Internet sharing'"
echo
echo " Then open:"
echo "   http://192.168.44.1:5000"
echo
echo " Works on Android & iOS"
echo "==========================================="
