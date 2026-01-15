#!/bin/bash
set -e

echo "=== Enabling HEADLESS Bluetooth PAN (No PIN / No Code) ==="

# ---- Packages ----
sudo apt update
sudo apt install -y bluetooth bluez bluez-tools bridge-utils dnsmasq

# ---- Enable Bluetooth ----
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# ---- BlueZ main config ----
CONF="/etc/bluetooth/main.conf"

sudo sed -i 's/^#*ControllerMode.*/ControllerMode = dual/' "$CONF"
sudo sed -i 's/^#*EnableNetwork.*/EnableNetwork = true/' "$CONF"
sudo sed -i 's/^#*DiscoverableTimeout.*/DiscoverableTimeout = 0/' "$CONF"
sudo sed -i 's/^#*PairableTimeout.*/PairableTimeout = 0/' "$CONF"
sudo sed -i 's/^#*AutoEnable.*/AutoEnable = true/' "$CONF"

# ---- Bluetooth daemon override: NoInputNoOutput ----
sudo mkdir -p /etc/systemd/system/bluetooth.service.d

sudo tee /etc/systemd/system/bluetooth.service.d/override.conf > /dev/null <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/libexec/bluetooth/bluetoothd --noplugin=sap --experimental
EOF

# ---- PAN systemd service ----
sudo tee /etc/systemd/system/bt-pan.service > /dev/null <<'EOF'
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

# ---- Network interface ----
sudo tee /etc/network/interfaces.d/pan0 > /dev/null <<'EOF'
auto pan0
iface pan0 inet static
    address 192.168.44.1
    netmask 255.255.255.0
EOF

# ---- DHCP (dnsmasq) ----
sudo tee /etc/dnsmasq.d/bt-pan.conf > /dev/null <<'EOF'
interface=pan0
dhcp-range=192.168.44.10,192.168.44.50,255.255.255.0,12h
EOF

# ---- Auto pairing & trust agent ----
sudo tee /usr/local/bin/bt-auto-agent.sh > /dev/null <<'EOF'
#!/bin/bash
bluetoothctl <<EOT
power on
agent NoInputNoOutput
default-agent
discoverable on
pairable on
trust *
exit
EOT
EOF

sudo chmod +x /usr/local/bin/bt-auto-agent.sh

# ---- Run agent at boot ----
sudo tee /etc/systemd/system/bt-agent.service > /dev/null <<'EOF'
[Unit]
Description=Bluetooth Auto Pairing Agent
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/bt-auto-agent.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# ---- Enable services ----
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
sudo systemctl enable bt-pan.service
sudo systemctl enable bt-agent.service
sudo systemctl restart dnsmasq
sudo systemctl start bt-pan.service
sudo systemctl start bt-agent.service

echo
echo "=============================================="
echo " HEADLESS BLUETOOTH PAN ENABLED"
echo
echo " • No PIN / No confirmation required"
echo " • Discoverable FOREVER"
echo " • Auto-trusts all devices"
echo
echo " Connect phone → enable Bluetooth tethering"
echo " Then open:"
echo "   http://192.168.44.1:5000"
echo "=============================================="
