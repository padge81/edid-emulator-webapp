#!/bin/bash
set -e

USER_NAME=$(whoami)
HOME_DIR="$HOME"
APP_DIR="$HOME_DIR/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
SCRIPT_PATH="$APP_DIR/start_edid_ui.sh"
DESKTOP_FILE="$HOME_DIR/Desktop/EDID-Emulator.desktop"
SYSTEMD_DIR="$HOME_DIR/.config/systemd/user"
SERVICE_FILE="$SYSTEMD_DIR/edid-emulator.service"
URL="http://127.0.0.1:5000"

echo "========================================"
echo " EDID Emulator Kiosk Setup"
echo " DSI-1 Portrait + Touch + Kiosk Mode"
echo "========================================"

echo "Installing dependencies..."
sudo apt update
sudo apt install -y epiphany-browser curl

echo "Creating launcher script..."
cat > "$SCRIPT_PATH" << 'EOF'
#!/bin/bash

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
URL="http://127.0.0.1:5000"

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

# --- Rotate DSI display to portrait ---
xrandr --output DSI-1 --rotate right

# --- Map touchscreen to display (libinput-safe) ---
TOUCH_ID=$(xinput list | grep -i 'ft5x06' | grep -o 'id=[0-9]*' | cut -d= -f2)
if [ -n "$TOUCH_ID" ]; then
    xinput map-to-output "$TOUCH_ID" DSI-1
fi

cd "$BACKEND_DIR"

# Activate venv if present
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Start Flask backend
python3 app.py &

# Wait for Flask to respond
for i in {1..20}; do
    curl -s "$URL" >/dev/null && break
    sleep 1
done

# Launch Epiphany in kiosk (application) mode
epiphany --application-mode "$URL" &

wait
EOF

chmod +x "$SCRIPT_PATH"

echo "Creating desktop launcher..."
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=EDID Emulator
Comment=Launch EDID Emulator UI
Exec=$SCRIPT_PATH
Icon=utilities-terminal
Terminal=false
Categories=Utility;
StartupNotify=false
EOF

chmod +x "$DESKTOP_FILE"

echo "Creating systemd user service..."
mkdir -p "$SYSTEMD_DIR"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=EDID Emulator UI (Kiosk)
After=graphical-session.target network-online.target

[Service]
Type=simple
ExecStart=$SCRIPT_PATH
Restart=on-failure
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME_DIR/.Xauthority

[Install]
WantedBy=default.target
EOF

echo "Enabling systemd user service..."
systemctl --user daemon-reexec
systemctl --user daemon-reload
systemctl --user enable edid-emulator.service

echo "Enabling lingering..."
sudo loginctl enable-linger "$USER_NAME"

echo
echo "========================================"
echo " Setup complete!"
echo
echo "• Fullscreen kiosk mode enabled"
echo "• DSI-1 portrait rotation applied"
echo "• Touchscreen aligned"
echo "• Auto-start on login enabled"
echo
echo "Reboot or log out/in to test."
echo "========================================"
