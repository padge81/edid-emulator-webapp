#!/bin/bash
set -e

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
SERVICE_DIR="$HOME/.config/systemd/user"

echo "=== EDID Emulator Kiosk Setup ==="

sudo apt update
sudo apt install -y curl chromium-browser

mkdir -p "$SERVICE_DIR"

cat > "$APP_DIR/start_edid_ui.sh" <<'EOF'
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

# Wait for X
for i in {1..30}; do
    if xset q >/dev/null 2>&1; then
        echo "X is ready"
        break
    fi
    echo "Waiting for X..."
    sleep 1
done

# Rotate display
xrandr --output DSI-1 --rotate right || echo "Rotation skipped"

# Map touchscreen
TOUCH_ID=$(xinput list | grep -i 'ft5x06' | grep -o 'id=[0-9]*' | cut -d= -f2)
if [ -n "$TOUCH_ID" ]; then
    echo "Mapping touchscreen ID $TOUCH_ID"
    xinput map-to-output "$TOUCH_ID" DSI-1
fi

# Start Flask
cd "$BACKEND_DIR" || exit 1
[ -f venv/bin/activate ] && source venv/bin/activate
echo "Starting Flask..."
python3 app.py &

for i in {1..30}; do
    curl -s "$URL" >/dev/null && break
    echo "Waiting for Flask..."
    sleep 1
done

# Launch browser
echo "Launching Chromium..."
chromium-browser --kiosk --start-fullscreen --disable-infobars --no-first-run --disable-session-crashed-bubble --force-device-scale-factor=1 "$URL" &

echo "Kiosk startup complete"
wait
EOF

chmod +x "$APP_DIR/start_edid_ui.sh"

cat > "$SERVICE_DIR/edid-emulator.service" <<EOF
[Unit]
Description=EDID Emulator Kiosk
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=$APP_DIR/start_edid_ui.sh
Restart=on-failure
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME/.Xauthority

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable edid-emulator.service

echo "Setup complete. Reboot recommended."
