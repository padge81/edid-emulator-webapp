#!/bin/bash
set -e

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
SERVICE_DIR="$HOME/.config/systemd/user"
DESKTOP_DIR="$HOME/Desktop"
DESKTOP_FILE="$DESKTOP_DIR/EDID_Emulator_Kiosk.desktop"

echo "=== EDID Emulator Chrome Kiosk Setup ==="

# ----------------------------
# Install required packages
# ----------------------------
sudo apt update
sudo apt install -y \
    chromium-browser \
    unclutter \
    wmctrl \
    xdotool \
    curl

# ----------------------------
# Remove old desktop icon
# ----------------------------
if [ -f "$DESKTOP_FILE" ]; then
    echo "Removing existing desktop icon"
    rm -f "$DESKTOP_FILE"
fi

# ----------------------------
# Create systemd user service dir
# ----------------------------
mkdir -p "$SERVICE_DIR"

# ----------------------------
# Create kiosk startup script
# ----------------------------
cat > "$APP_DIR/start_edid_kiosk.sh" <<'EOF'
#!/bin/bash

LOG="$HOME/edid_kiosk.log"
exec >>"$LOG" 2>&1
echo "==== Kiosk start: $(date) ===="

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
URL="http://127.0.0.1:5000"

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

echo "DISPLAY=$DISPLAY"
echo "XAUTHORITY=$XAUTHORITY"

# ----------------------------
# Wait for X to be ready
# ----------------------------
for i in {1..40}; do
    if xset q >/dev/null 2>&1; then
        echo "X is ready"
        break
    fi
    echo "Waiting for X..."
    sleep 1
done

# ----------------------------
# Rotate display (DSI touchscreen)
# ----------------------------
xrandr --output DSI-1 --rotate right || echo "Display rotation skipped"

# ----------------------------
# Touchscreen rotation fix (FT5x06)
# ----------------------------
TOUCH_NAME=$(xinput list --name-only | grep -i 'ft5x06\|ft5406' | head -n1)

if [ -n "$TOUCH_NAME" ]; then
    echo "Applying touch rotation matrix to: $TOUCH_NAME"
    xinput set-prop "$TOUCH_NAME" \
        "Coordinate Transformation Matrix" \
        0 1 0 \
       -1 0 1 \
        0 0 1
else
    echo "Touchscreen device not found"
fi

# ----------------------------
# Hide mouse cursor
# ----------------------------
unclutter -idle 0 &

# ----------------------------
# Start Flask backend
# ----------------------------
cd "$BACKEND_DIR" || exit 1
[ -f venv/bin/activate ] && source venv/bin/activate

echo "Starting Flask backend..."
python3 app.py &

# Wait for Flask
for i in {1..40}; do
    curl -s "$URL" >/dev/null && break
    echo "Waiting for Flask..."
    sleep 1
done

# ----------------------------
# Kill any existing Chromium
# ----------------------------
pkill -f chromium || true
sleep 1

# ----------------------------
# Launch Chromium in kiosk mode
# ----------------------------
echo "Launching Chromium kiosk..."
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-translate \
    --disable-features=TranslateUI \
    --check-for-update-interval=31536000 \
    "$URL" &

echo "Kiosk startup complete"
wait
EOF

chmod +x "$APP_DIR/start_edid_kiosk.sh"

# ----------------------------
# Create systemd user service
# ----------------------------
cat > "$SERVICE_DIR/edid-emulator.service" <<EOF
[Unit]
Description=EDID Emulator Chrome Kiosk
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=$APP_DIR/start_edid_kiosk.sh
Restart=on-failure
Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority

[Install]
WantedBy=default.target
EOF

# ----------------------------
# Enable service
# ----------------------------
systemctl --user daemon-reload
systemctl --user enable edid-emulator.service

# ----------------------------
# Create desktop launcher
# ----------------------------
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=EDID Emulator Kiosk
Comment=Launch EDID Emulator Kiosk
Exec=$APP_DIR/start_edid_kiosk.sh
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Utility;
EOF

chmod +x "$DESKTOP_FILE"

echo "======================================"
echo " Setup complete ✔"
echo " Reboot recommended"
echo " Desktop icon created: EDID Emulator Kiosk"
echo "======================================"
