#!/bin/bash
set -e

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
SERVICE_DIR="$HOME/.config/systemd/user"
DESKTOP_DIR="$HOME/Desktop"

KIOSK_SCRIPT="$APP_DIR/start_edid_kiosk.sh"
DESKTOP_ICON="$DESKTOP_DIR/EDID_Emulator.desktop"

URL="http://127.0.0.1:5000"
DISPLAY_NAME="DSI-1"

echo "=== EDID Emulator Chromium Kiosk Setup ==="

# ------------------------------------------------------------
# Packages
# ------------------------------------------------------------
sudo apt update
sudo apt install -y \
    chromium-browser \
    unclutter \
    xinput \
    x11-xserver-utils \
    curl

# Optional cleanup of Epiphany stack
sudo apt purge -y epiphany-browser wmctrl xdotool || true
sudo apt autoremove -y

mkdir -p "$SERVICE_DIR"
mkdir -p "$DESKTOP_DIR"

# ------------------------------------------------------------
# Kiosk start script
# ------------------------------------------------------------
cat > "$KIOSK_SCRIPT" <<'EOF'
#!/bin/bash

LOG="$HOME/edid_kiosk.log"
exec >>"$LOG" 2>&1
echo "==== Kiosk start: $(date) ===="

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
URL="http://127.0.0.1:5000"

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

# ------------------------------------------------------------
# Wait for X server
# ------------------------------------------------------------
for i in {1..30}; do
    if xset q >/dev/null 2>&1; then
        echo "X server ready"
        break
    fi
    sleep 1
done

# ------------------------------------------------------------
# Rotate screen
# ------------------------------------------------------------
xrandr --output DSI-1 --rotate right || echo "Rotation skipped"

# ------------------------------------------------------------
# Rotate touchscreen
# ------------------------------------------------------------
TOUCH_ID=$(xinput list --id-only "FT5406 memory based driver" 2>/dev/null || true)
if [ -n "$TOUCH_ID" ]; then
    echo "Mapping touchscreen ID $TOUCH_ID"
    xinput map-to-output "$TOUCH_ID" DSI-1
fi

# ------------------------------------------------------------
# Hide cursor (touchscreen friendly)
# ------------------------------------------------------------
unclutter -idle 0 &

# ------------------------------------------------------------
# Start Flask backend
# ------------------------------------------------------------
cd "$BACKEND_DIR" || exit 1
[ -f venv/bin/activate ] && source venv/bin/activate
python3 app.py &

# Wait for Flask
for i in {1..30}; do
    curl -s "$URL" >/dev/null && break
    sleep 1
done

# ------------------------------------------------------------
# Launch Chromium in kiosk mode
# ------------------------------------------------------------
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-translate \
    --disable-features=TranslateUI \
    --overscroll-history-navigation=0 \
    "$URL" &

wait
EOF

chmod +x "$KIOSK_SCRIPT"

# ------------------------------------------------------------
# systemd user service
# ------------------------------------------------------------
cat > "$SERVICE_DIR/edid-emulator.service" <<EOF
[Unit]
Description=EDID Emulator Chromium Kiosk
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=$KIOSK_SCRIPT
Restart=on-failure
Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable edid-emulator.service

# ------------------------------------------------------------
# Desktop launcher icon
# ------------------------------------------------------------
cat > "$DESKTOP_ICON" <<EOF
[Desktop Entry]
Name=EDID Emulator
Comment=Launch EDID Emulator Kiosk
Exec=$KIOSK_SCRIPT
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Utility;
EOF

chmod +x "$DESKTOP_ICON"

# ------------------------------------------------------------
# Allow desktop icon execution
# ------------------------------------------------------------
gio set "$DESKTOP_ICON" metadata::trusted true || true

echo "=========================================="
echo " Setup complete."
echo " - Chromium kiosk enabled on login"
echo " - Screen + touch rotated"
echo " - Cursor hidden"
echo " - Desktop icon created"
echo
echo " Reboot recommended."
echo "=========================================="
